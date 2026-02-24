"""环保咨询助手核心模块。

功能：
1. 环保法规知识库检索（内置生态环境部公开站点来源）。
2. 企业合规建议生成（基于行业、排污场景、风险等级的规则引擎）。
3. 本地 SQLite 数据库上传/导入，扩展企业自有法规与台账数据。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable
import re
import sqlite3


DEFAULT_SOURCES = {
    "生态环境部（法规标准）": "https://www.mee.gov.cn/ywgz/fgbz/",
    "排污许可专题": "https://www.mee.gov.cn/ywgz/pwxkgl/",
    "全国排污许可证管理信息平台（公开端）": "https://permit.mee.gov.cn/",
}


@dataclass(slots=True)
class RegulationDoc:
    title: str
    content: str
    source: str
    tags: list[str] = field(default_factory=list)


class EnvironmentalConsultingAssistant:
    """环保咨询助手。"""

    def __init__(self) -> None:
        self.docs: list[RegulationDoc] = []
        self.sources: dict[str, str] = dict(DEFAULT_SOURCES)
        self._seed_builtin_knowledge()

    def _seed_builtin_knowledge(self) -> None:
        self.docs.extend(
            [
                RegulationDoc(
                    title="排污许可管理要点",
                    source="排污许可专题",
                    tags=["排污许可", "申请", "变更", "台账"],
                    content=(
                        "企业应按行业分类开展排污许可证申请、延续与变更；"
                        "重点核查污染物排放口、执行标准、监测频次和自行监测方案。"
                    ),
                ),
                RegulationDoc(
                    title="固体废物合规管理检查清单",
                    source="生态环境部（法规标准）",
                    tags=["固废", "危废", "转移联单", "台账"],
                    content=(
                        "危险废物应分类贮存并规范设置标识，建立台账与转移联单；"
                        "委托处置单位应具备相应资质并签订合规协议。"
                    ),
                ),
                RegulationDoc(
                    title="废水与废气达标排放核查",
                    source="生态环境部（法规标准）",
                    tags=["废水", "废气", "达标排放", "在线监测"],
                    content=(
                        "核查污染物因子是否覆盖许可要求，确保监测点位、监测方法、"
                        "监测频次与执行标准一致，异常情况应留痕并及时整改。"
                    ),
                ),
            ]
        )

    def upload_sqlite_database(
        self,
        db_path: str | Path,
        table: str,
        title_col: str,
        content_col: str,
        source_name: str = "企业上传数据库",
    ) -> int:
        """从 SQLite 表导入法规/制度文本。

        Args:
            db_path: SQLite 文件路径。
            table: 目标表名。
            title_col: 标题列名。
            content_col: 内容列名。
            source_name: 导入来源名称。
        Returns:
            成功导入的记录条数。
        """
        db_path = Path(db_path)
        if not db_path.exists():
            raise FileNotFoundError(f"数据库不存在: {db_path}")

        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute(
                f"SELECT {title_col}, {content_col} FROM {table}"  # noqa: S608, controlled by caller
            )
            rows = cursor.fetchall()

        imported = 0
        for title, content in rows:
            if not title or not content:
                continue
            tags = self._extract_tags(str(title) + " " + str(content))
            self.docs.append(
                RegulationDoc(
                    title=str(title),
                    content=str(content),
                    source=source_name,
                    tags=tags,
                )
            )
            imported += 1

        return imported

    def search_regulations(self, query: str, top_k: int = 5) -> list[RegulationDoc]:
        """按关键词命中数检索法规文档。"""
        tokens = self._tokenize(query)
        if not tokens:
            return []

        scored: list[tuple[int, RegulationDoc]] = []
        for doc in self.docs:
            haystack = f"{doc.title} {doc.content} {' '.join(doc.tags)}"
            score = sum(1 for token in tokens if token in haystack)
            if score > 0:
                scored.append((score, doc))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [doc for _, doc in scored[:top_k]]

    def generate_compliance_advice(
        self,
        industry: str,
        pollutants: Iterable[str],
        has_permit: bool,
        has_monitoring_plan: bool,
    ) -> str:
        """生成企业合规建议。"""
        pollutants = [p.strip() for p in pollutants if p and p.strip()]
        risk_points: list[str] = []
        actions: list[str] = []

        if not has_permit:
            risk_points.append("未持证排污风险")
            actions.append("尽快核定行业类别与排污单元，申请或变更排污许可证。")
        if not has_monitoring_plan:
            risk_points.append("自行监测计划缺失风险")
            actions.append("建立自行监测方案，明确监测因子、频次和责任岗位。")

        if any(k in pollutants for k in ("COD", "氨氮", "总磷", "总氮")):
            actions.append("重点复核废水处理设施稳定运行，保留药剂投加和运行台账。")
        if any(k in pollutants for k in ("VOC", "SO2", "NOx", "颗粒物")):
            actions.append("核查废气收集与治理效率，完善无组织排放巡检记录。")

        if not actions:
            actions.append("当前基础合规条件较完整，建议按季度开展内部环保审计。")

        refs = "\n".join(f"- {name}: {url}" for name, url in self.sources.items())
        risks = "、".join(risk_points) if risk_points else "当前未识别高风险项"
        return (
            f"【企业画像】行业：{industry}；关注污染物：{', '.join(pollutants) or '未提供'}\n"
            f"【风险判断】{risks}\n"
            "【建议措施】\n"
            + "\n".join(f"{idx + 1}. {action}" for idx, action in enumerate(actions))
            + "\n【建议核验来源】\n"
            + refs
        )

    def _tokenize(self, text: str) -> list[str]:
        text = text.lower().strip()
        return [tok for tok in re.split(r"[^\w\u4e00-\u9fff]+", text) if len(tok) >= 2]

    def _extract_tags(self, text: str) -> list[str]:
        candidates = ["排污许可", "危废", "固废", "废水", "废气", "监测", "台账", "整改", "标准"]
        return [c for c in candidates if c in text]


if __name__ == "__main__":
    assistant = EnvironmentalConsultingAssistant()
    demo_results = assistant.search_regulations("排污许可 监测 台账")
    print("=== 法规检索结果 ===")
    for i, doc in enumerate(demo_results, start=1):
        print(f"{i}. [{doc.source}] {doc.title}")

    print("\n=== 合规建议示例 ===")
    print(
        assistant.generate_compliance_advice(
            industry="电子制造",
            pollutants=["VOC", "COD"],
            has_permit=False,
            has_monitoring_plan=False,
        )
    )
