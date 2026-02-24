"""环保咨询助手核心模块（专业版 MVP）。

覆盖能力：
1) 环保法规查询：支持地区/行业/污染因子/状态过滤，输出条款级引用。
2) 企业合规建议：执行差距分析（Gap Analysis）并给出整改清单、证据清单、时限与风险分级。
3) 数据库上传：导入企业本地 SQLite 数据作为增量知识。

安全边界（硬规则）：
- 不输出“法律结论”，统一使用“依据…一般需要/建议…”表述；
- 涉及处罚、停产、刑责时输出“需法务/第三方复核”；
- 合规结论必须绑定条款引用。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
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
class RegulationClause:
    doc_title: str
    doc_no: str
    issuing_authority: str
    level: str  # 法律/行政法规/部门规章/标准/地方规范性文件等
    region: str  # 国家/省/市
    industry: str
    pollutant_factors: list[str]
    effective_status: str  # 生效/废止/修订中
    publish_date: str
    article_ref: str  # 第几条/款/附录/表
    quote: str
    obligations: list[str]
    prohibitions: list[str]
    penalties: list[str]
    source_name: str
    source_url: str
    tags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RegulationSearchResult:
    title: str
    applicability: str
    key_obligations: list[str]
    key_prohibitions: list[str]
    legal_liability: list[str]
    execution_points: list[str]
    citation: str
    quote: str
    effective_status: str


@dataclass(slots=True)
class GapItem:
    topic: str
    risk_level: str
    deadline_days: int
    owner: str
    actions: list[str]
    evidence: list[str]
    references: list[str]


class EnvironmentalConsultingAssistant:
    """环保咨询助手。"""

    def __init__(self) -> None:
        self.sources: dict[str, str] = dict(DEFAULT_SOURCES)
        self.regulation_clauses: list[RegulationClause] = []
        self._seed_builtin_knowledge()

    def _seed_builtin_knowledge(self) -> None:
        self.regulation_clauses.extend(
            [
                RegulationClause(
                    doc_title="排污许可管理条例（示例知识条目）",
                    doc_no="国令示例第XX号",
                    issuing_authority="生态环境主管部门",
                    level="行政法规",
                    region="国家",
                    industry="通用",
                    pollutant_factors=["COD", "氨氮", "VOC", "颗粒物"],
                    effective_status="生效",
                    publish_date="2021-01-01",
                    article_ref="第十八条",
                    quote="实行排污许可管理的企业事业单位应当按照排污许可证规定排放污染物。",
                    obligations=["依法申请、延续、变更排污许可证", "按证排污并执行许可限值"],
                    prohibitions=["无证排污", "超许可排放"],
                    penalties=["可能被责令改正并处罚款"],
                    source_name="排污许可专题",
                    source_url=DEFAULT_SOURCES["排污许可专题"],
                    tags=["排污许可", "按证排污"],
                ),
                RegulationClause(
                    doc_title="危险废物贮存污染控制标准（示例知识条目）",
                    doc_no="GB 18597（示例）",
                    issuing_authority="生态环境部/市场监管总局",
                    level="国家标准",
                    region="国家",
                    industry="通用",
                    pollutant_factors=["危废"],
                    effective_status="生效",
                    publish_date="2023-07-01",
                    article_ref="第6章",
                    quote="危险废物贮存设施应采取防渗漏、防流失、防扬散等措施，并设置识别标志。",
                    obligations=["危废分类分区贮存", "建立危废出入库台账"],
                    prohibitions=["危废混存混放", "标识缺失"],
                    penalties=["可能触发危废管理违法风险"],
                    source_name="生态环境部（法规标准）",
                    source_url=DEFAULT_SOURCES["生态环境部（法规标准）"],
                    tags=["危废", "暂存间", "台账"],
                ),
                RegulationClause(
                    doc_title="排污单位自行监测技术指南（示例知识条目）",
                    doc_no="HJ 819（示例）",
                    issuing_authority="生态环境部",
                    level="行业标准",
                    region="国家",
                    industry="通用",
                    pollutant_factors=["COD", "氨氮", "VOC", "SO2", "NOx"],
                    effective_status="生效",
                    publish_date="2017-06-01",
                    article_ref="5.2条",
                    quote="排污单位应按排污许可证和相关标准要求确定监测指标、频次和点位。",
                    obligations=["制定并执行自行监测方案", "保存监测原始记录和报告"],
                    prohibitions=["漏测应测因子", "篡改监测数据"],
                    penalties=["可能导致许可证执行不符合及行政处罚风险"],
                    source_name="排污许可专题",
                    source_url=DEFAULT_SOURCES["排污许可专题"],
                    tags=["自行监测", "频次", "因子"],
                ),
                RegulationClause(
                    doc_title="建设项目环境保护管理条例（示例知识条目）",
                    doc_no="国务院令第682号（示例）",
                    issuing_authority="国务院",
                    level="行政法规",
                    region="国家",
                    industry="通用",
                    pollutant_factors=["三同时"],
                    effective_status="生效",
                    publish_date="2017-10-01",
                    article_ref="第十九条",
                    quote="配套建设的环境保护设施经验收合格，主体工程方可投入生产或者使用。",
                    obligations=["环评审批后建设", "环保设施三同时", "依法组织竣工环保验收"],
                    prohibitions=["未验先投"],
                    penalties=["可能被责令停止生产并处罚"],
                    source_name="生态环境部（法规标准）",
                    source_url=DEFAULT_SOURCES["生态环境部（法规标准）"],
                    tags=["环评", "验收", "三同时"],
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
        """从 SQLite 表导入企业制度/法规文本。"""
        db_path = Path(db_path)
        if not db_path.exists():
            raise FileNotFoundError(f"数据库不存在: {db_path}")

        with sqlite3.connect(db_path) as conn:
            rows = conn.execute(
                f"SELECT {title_col}, {content_col} FROM {table}"  # noqa: S608
            ).fetchall()

        imported = 0
        for title, content in rows:
            if not title or not content:
                continue
            text = f"{title} {content}"
            self.regulation_clauses.append(
                RegulationClause(
                    doc_title=str(title),
                    doc_no="企业内控文件",
                    issuing_authority="企业内部",
                    level="规范性文件",
                    region="企业",
                    industry="企业自定义",
                    pollutant_factors=self._extract_pollutants(text),
                    effective_status="生效",
                    publish_date=str(date.today()),
                    article_ref="内部条款",
                    quote=str(content)[:120],
                    obligations=["依据企业制度执行"],
                    prohibitions=[],
                    penalties=[],
                    source_name=source_name,
                    source_url="内部数据库",
                    tags=self._extract_tags(text),
                )
            )
            imported += 1
        return imported

    def search_regulations(
        self,
        query: str,
        region: str | None = None,
        industry: str | None = None,
        pollutant: str | None = None,
        effective_status: str = "生效",
        top_k: int = 5,
    ) -> list[RegulationSearchResult]:
        """法规查询（条款级定位 + 可追溯引用）。"""
        tokens = self._tokenize(query)
        scored: list[tuple[int, RegulationClause]] = []

        for clause in self.regulation_clauses:
            if effective_status and clause.effective_status != effective_status:
                continue
            if region and clause.region not in ("国家", region):
                continue
            if industry and clause.industry not in ("通用", industry):
                continue
            if pollutant and pollutant not in clause.pollutant_factors and pollutant not in clause.tags:
                continue

            haystack = " ".join(
                [
                    clause.doc_title,
                    clause.quote,
                    clause.article_ref,
                    " ".join(clause.tags),
                    " ".join(clause.obligations),
                    " ".join(clause.prohibitions),
                ]
            )
            score = sum(1 for t in tokens if t in haystack)
            if score:
                scored.append((score, clause))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [self._format_search_result(c) for _, c in scored[:top_k]]

    def gap_analysis(self, profile: dict[str, object]) -> list[GapItem]:
        """合规差距分析：输出可执行、可审计清单。"""
        industry = str(profile.get("industry", "未说明"))
        has_permit = bool(profile.get("has_permit", False))
        has_monitoring_plan = bool(profile.get("has_monitoring_plan", False))
        has_haz_waste_room = bool(profile.get("has_haz_waste_room", False))
        has_eia_acceptance = bool(profile.get("has_eia_acceptance", False))

        items: list[GapItem] = []
        if not has_permit:
            refs = self.search_regulations("排污许可 按证排污", industry=industry, top_k=2)
            items.append(
                GapItem(
                    topic="排污许可与按证排污",
                    risk_level="高",
                    deadline_days=7,
                    owner="环保经理",
                    actions=[
                        "核对排污单元、排口、执行标准并补齐许可证申请/变更材料",
                        "建立许可证执行台账与年度执行报告机制",
                    ],
                    evidence=["排污许可证副本", "申请表与受理回执", "年度执行报告"],
                    references=[r.citation for r in refs],
                )
            )

        if not has_monitoring_plan:
            refs = self.search_regulations("自行监测 频次 因子", industry=industry, top_k=2)
            items.append(
                GapItem(
                    topic="自行监测与台账",
                    risk_level="高",
                    deadline_days=30,
                    owner="监测主管",
                    actions=["制定监测方案（点位/因子/频次）", "建立监测原始记录和异常闭环"],
                    evidence=["自行监测方案", "监测报告", "异常整改闭环单"],
                    references=[r.citation for r in refs],
                )
            )

        if not has_haz_waste_room:
            refs = self.search_regulations("危废 暂存间 标识 台账", industry=industry, top_k=2)
            items.append(
                GapItem(
                    topic="危险废物规范化管理",
                    risk_level="中",
                    deadline_days=30,
                    owner="危废管理员",
                    actions=["设置防渗防雨暂存区并张贴标识", "执行出入库台账与转移联单"],
                    evidence=["危废暂存间照片", "出入库台账", "转移联单"],
                    references=[r.citation for r in refs],
                )
            )

        if not has_eia_acceptance:
            refs = self.search_regulations("环评 验收 三同时", industry=industry, top_k=2)
            items.append(
                GapItem(
                    topic="环评/验收/三同时",
                    risk_level="高",
                    deadline_days=90,
                    owner="项目负责人",
                    actions=["梳理新增生产线是否触发环评变更", "依法组织竣工环保验收并留痕"],
                    evidence=["环评批复", "验收报告", "三同时落实记录"],
                    references=[r.citation for r in refs],
                )
            )

        return items

    def generate_compliance_advice(self, profile: dict[str, object]) -> str:
        """生成面向企业执行的合规建议（含安全边界与引用）。"""
        industry = str(profile.get("industry", "未说明"))
        region = str(profile.get("region", "未说明"))
        pollutants = ", ".join(profile.get("pollutants", []) or ["未提供"])  # type: ignore[arg-type]

        gaps = self.gap_analysis(profile)
        if not gaps:
            return (
                "依据现有信息，暂未识别明显高风险差距。建议按季度复核许可证执行、监测台账与危废管理。\n"
                "说明：本助手不构成法律结论，具体事项建议由法务/第三方复核。"
            )

        lines = [
            "【合规体检画像】",
            f"- 地区：{region}",
            f"- 行业：{industry}",
            f"- 关注因子：{pollutants}",
            "",
            "【Gap Analysis（差距项）】",
        ]

        for idx, item in enumerate(gaps, start=1):
            lines.extend(
                [
                    f"{idx}. {item.topic}（风险：{item.risk_level}，建议时限：{item.deadline_days}天，责任人：{item.owner}）",
                    f"   - 建议措施：{'；'.join(item.actions)}",
                    f"   - 证据材料：{'；'.join(item.evidence)}",
                    f"   - 依据引用：{' | '.join(item.references) or '建议补充法规引用'}",
                ]
            )

        lines.extend(
            [
                "",
                "【监管问询口径（建议表达）】",
                "- 依据现行生态环境法规条款，我们一般需要按证排污、按方案监测并保留台账证据，正在按计划整改。",
                "- 涉及处罚、停产、刑责等高风险事项，建议由法务或第三方机构复核后对外回复。",
                "",
                "【安全边界声明】",
                "- 本助手提供合规辅助意见，不构成法律结论或执法认定。",
                "- 所有合规结论应以引用条款和最新有效文本为准。",
            ]
        )
        return "\n".join(lines)

    def answer_user_question(self, question: str, profile: dict[str, object]) -> str:
        """面向用户的问答入口：自动检索法规并生成引用化回答。"""
        hits = self.search_regulations(
            query=question,
            region=str(profile.get("region", "")) or None,
            industry=str(profile.get("industry", "")) or None,
            top_k=3,
        )

        if not hits:
            return "未检索到匹配条款，请补充地区/行业/污染因子信息后重试。"

        blocks = ["【法规依据与执行建议】"]
        for i, h in enumerate(hits, start=1):
            blocks.extend(
                [
                    f"{i}. 适用范围：{h.applicability}",
                    f"   - 关键义务：{'；'.join(h.key_obligations)}",
                    f"   - 禁止事项：{'；'.join(h.key_prohibitions) if h.key_prohibitions else '按条款执行'}",
                    f"   - 执行要点：{'；'.join(h.execution_points)}",
                    f"   - 条款摘录：{h.quote}",
                    f"   - 引用：{h.citation}（状态：{h.effective_status}）",
                ]
            )
        blocks.append("说明：以上为合规辅助意见，不构成法律结论；高风险事项建议法务复核。")
        return "\n".join(blocks)

    def _format_search_result(self, clause: RegulationClause) -> RegulationSearchResult:
        return RegulationSearchResult(
            title=clause.doc_title,
            applicability=f"{clause.region} / {clause.industry} / {clause.level}",
            key_obligations=clause.obligations,
            key_prohibitions=clause.prohibitions,
            legal_liability=clause.penalties,
            execution_points=["结合企业排口与工艺建立执行台账", "按条款要求进行内部核查和整改留痕"],
            citation=(
                f"{clause.doc_title} {clause.article_ref}，{clause.doc_no}，"
                f"{clause.issuing_authority}，来源：{clause.source_name}({clause.source_url})"
            ),
            quote=clause.quote,
            effective_status=clause.effective_status,
        )

    def _tokenize(self, text: str) -> list[str]:
        text = text.lower().strip()
        raw_tokens = [tok for tok in re.split(r"[^\w\u4e00-\u9fff]+", text) if tok]
        tokens: list[str] = []
        for tok in raw_tokens:
            if len(tok) < 2:
                continue
            tokens.append(tok)
            if re.search(r"[\u4e00-\u9fff]", tok) and len(tok) >= 4:
                tokens.extend(tok[i : i + 2] for i in range(len(tok) - 1))
        return list(dict.fromkeys(tokens))

    def _extract_tags(self, text: str) -> list[str]:
        candidates = ["排污许可", "危废", "固废", "废水", "废气", "监测", "台账", "整改", "标准"]
        return [c for c in candidates if c in text]

    def _extract_pollutants(self, text: str) -> list[str]:
        keywords = ["COD", "氨氮", "总磷", "总氮", "VOC", "SO2", "NOx", "颗粒物", "危废"]
        return [k for k in keywords if k in text]


if __name__ == "__main__":
    assistant = EnvironmentalConsultingAssistant()
    profile_demo = {
        "region": "新疆",
        "industry": "石油化工",
        "pollutants": ["VOC", "COD"],
        "has_permit": False,
        "has_monitoring_plan": False,
        "has_haz_waste_room": False,
        "has_eia_acceptance": False,
    }

    print("=== 问题1：危废暂存间要求 ===")
    print(assistant.answer_user_question("危废暂存间需要满足哪些要求？依据是什么？", profile_demo))
    print("\n=== 问题2：自行监测频次与台账 ===")
    print(assistant.answer_user_question("排污许可里自行监测频次怎么定，哪些因子必须测？", profile_demo))
    print("\n=== 问题3：新增产线流程与风险 ===")
    print(assistant.answer_user_question("新增生产线，环评验收排污许可流程和风险是什么？", profile_demo))
    print("\n=== 合规整改计划 ===")
    print(assistant.generate_compliance_advice(profile_demo))
