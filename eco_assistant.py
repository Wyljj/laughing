"""全国环保与职业卫生咨询助手（MVP）。

能力底座：
1) 法规检索：条款级引用、全国/地方适用、现行有效过滤。
2) 危废合规建议：问诊式差距分析（Gap）+ 整改计划（7/30/90天）+ 证据链。
3) 咨询评估：输出可审计的咨询结论模板（非法律裁决）。

硬约束：
- 无引用不下结论；
- 不做法律裁决，仅给“依据 + 一般要求 + 建议动作”；
- 涉及停产整治/重大违法/刑责边界，自动触发高风险复核提示。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
import re
import sqlite3


DEFAULT_SOURCES = {
    "生态环境部（法规标准）": "https://www.mee.gov.cn/ywgz/fgbz/",
    "排污许可专题": "https://www.mee.gov.cn/ywgz/pwxkgl/",
    "全国排污许可证管理信息平台（公开端）": "https://permit.mee.gov.cn/",
}

LEVEL_PRIORITY = {
    "法律": 1,
    "行政法规": 2,
    "部门规章": 3,
    "地方性法规": 4,
    "地方政府规章": 5,
    "国家标准": 6,
    "行业标准": 7,
    "地方标准": 8,
    "规范性文件": 9,
    "口径类": 10,
}


@dataclass(slots=True)
class RegulationClause:
    doc_title: str
    doc_type: str
    doc_no: str
    issuer: str
    region: str
    region_code: str
    industry_tags: list[str]
    pollutant_factors: list[str]
    effective_date: str
    expire_date: str | None
    status: str
    article_id: str
    quote: str
    obligations: list[str]
    prohibitions: list[str]
    penalties: list[str]
    source_url: str
    source_name: str
    tags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RegulationSearchResult:
    summary: str
    applicability: str
    legal_basis: list[str]
    action_points: list[str]
    citations: list[str]
    evidence_points: list[str]


@dataclass(slots=True)
class GapItem:
    scene: str
    gap: str
    risk_level: str
    plan_days: int
    owner_role: str
    actions: list[str]
    evidence_chain: list[str]
    citations: list[str]


class EnvironmentalConsultingAssistant:
    def __init__(self) -> None:
        self.sources = dict(DEFAULT_SOURCES)
        self.regulation_clauses: list[RegulationClause] = []
        self._seed_builtin_knowledge()

    def _seed_builtin_knowledge(self) -> None:
        self.regulation_clauses.extend(
            [
                RegulationClause(
                    doc_title="中华人民共和国固体废物污染环境防治法（示例条目）",
                    doc_type="法律",
                    doc_no="主席令第43号（示例）",
                    issuer="全国人大常委会",
                    region="全国",
                    region_code="CN",
                    industry_tags=["通用"],
                    pollutant_factors=["危废"],
                    effective_date="2020-09-01",
                    expire_date=None,
                    status="现行有效",
                    article_id="第八十一条",
                    quote="产生危险废物的单位应当按照国家规定制定危险废物管理计划并建立台账。",
                    obligations=["建立危废台账", "制定危废管理计划"],
                    prohibitions=["非法倾倒、堆放、处置危废"],
                    penalties=["可能面临罚款及停产整治风险"],
                    source_url=DEFAULT_SOURCES["生态环境部（法规标准）"],
                    source_name="生态环境部（法规标准）",
                    tags=["危废", "台账", "管理计划"],
                ),
                RegulationClause(
                    doc_title="危险废物贮存污染控制标准（示例条目）",
                    doc_type="国家标准",
                    doc_no="GB 18597（示例）",
                    issuer="生态环境部/市场监管总局",
                    region="全国",
                    region_code="CN",
                    industry_tags=["通用"],
                    pollutant_factors=["危废"],
                    effective_date="2023-07-01",
                    expire_date=None,
                    status="现行有效",
                    article_id="6.1条",
                    quote="危险废物贮存设施应具备防渗漏、防流失、防扬散措施并规范标识。",
                    obligations=["危废分类分区贮存", "设置规范标识"],
                    prohibitions=["混存混放", "无标识存放"],
                    penalties=["可能触发危废规范化检查不符合"],
                    source_url=DEFAULT_SOURCES["生态环境部（法规标准）"],
                    source_name="生态环境部（法规标准）",
                    tags=["暂存间", "标识", "防渗"],
                ),
                RegulationClause(
                    doc_title="排污许可管理条例（示例条目）",
                    doc_type="行政法规",
                    doc_no="国务院令第736号（示例）",
                    issuer="国务院",
                    region="全国",
                    region_code="CN",
                    industry_tags=["通用"],
                    pollutant_factors=["COD", "VOC", "氨氮"],
                    effective_date="2021-03-01",
                    expire_date=None,
                    status="现行有效",
                    article_id="第十八条",
                    quote="排污单位应当按照排污许可证规定排放污染物并开展自行监测。",
                    obligations=["按证排污", "执行自行监测"],
                    prohibitions=["无证排污", "超许可排放"],
                    penalties=["可能被责令改正并处罚款"],
                    source_url=DEFAULT_SOURCES["排污许可专题"],
                    source_name="排污许可专题",
                    tags=["排污许可", "自行监测"],
                ),
                RegulationClause(
                    doc_title="新疆维吾尔自治区危险废物污染环境防治办法（示例条目）",
                    doc_type="地方政府规章",
                    doc_no="新政规〔示例〕12号",
                    issuer="新疆维吾尔自治区人民政府",
                    region="新疆",
                    region_code="650000",
                    industry_tags=["通用"],
                    pollutant_factors=["危废"],
                    effective_date="2022-01-01",
                    expire_date=None,
                    status="现行有效",
                    article_id="第二十二条",
                    quote="危废暂存超过规定期限或去向不明的，应立即报告并整改。",
                    obligations=["控制暂存期限", "异常情况报告"],
                    prohibitions=["超期暂存", "去向不明"],
                    penalties=["可能被从重处理"],
                    source_url=DEFAULT_SOURCES["生态环境部（法规标准）"],
                    source_name="地方公开文件（示例）",
                    tags=["新疆", "危废", "地方更严"],
                ),
                RegulationClause(
                    doc_title="工作场所有害因素职业接触限值（示例条目）",
                    doc_type="国家标准",
                    doc_no="GBZ 2.1（示例）",
                    issuer="国家卫生健康委",
                    region="全国",
                    region_code="CN",
                    industry_tags=["职业卫生", "通用"],
                    pollutant_factors=["职业卫生", "粉尘", "苯"],
                    effective_date="2019-01-01",
                    expire_date=None,
                    status="现行有效",
                    article_id="附录A",
                    quote="应对工作场所有害因素进行识别与定期检测，确保接触水平满足限值要求。",
                    obligations=["有害因素识别", "职业卫生检测与评价"],
                    prohibitions=["超限值长期暴露"],
                    penalties=["可能触发职业健康合规风险"],
                    source_url="国家职业卫生标准公开渠道（示例）",
                    source_name="职业卫生标准（示例）",
                    tags=["职业卫生", "检测", "限值"],
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
        db_path = Path(db_path)
        if not db_path.exists():
            raise FileNotFoundError(f"数据库不存在: {db_path}")

        with sqlite3.connect(db_path) as conn:
            rows = conn.execute(f"SELECT {title_col}, {content_col} FROM {table}").fetchall()  # noqa: S608

        imported = 0
        for title, content in rows:
            if not title or not content:
                continue
            text = f"{title} {content}"
            self.regulation_clauses.append(
                RegulationClause(
                    doc_title=str(title),
                    doc_type="规范性文件",
                    doc_no="企业内控文件",
                    issuer="企业内部",
                    region="企业",
                    region_code="ORG",
                    industry_tags=["企业自定义"],
                    pollutant_factors=self._extract_pollutants(text),
                    effective_date=str(date.today()),
                    expire_date=None,
                    status="现行有效",
                    article_id="内部条款",
                    quote=str(content)[:120],
                    obligations=["按企业内控制度执行"],
                    prohibitions=[],
                    penalties=[],
                    source_url="内部数据库",
                    source_name=source_name,
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
        status: str = "现行有效",
        top_k: int = 5,
    ) -> list[RegulationClause]:
        tokens = self._tokenize(query)
        candidates: list[tuple[tuple[int, int, int], RegulationClause]] = []

        for clause in self.regulation_clauses:
            if status and clause.status != status:
                continue
            if region and clause.region not in ("全国", region, "企业"):
                continue
            if industry and "通用" not in clause.industry_tags and industry not in clause.industry_tags:
                continue
            if pollutant and pollutant not in clause.pollutant_factors and pollutant not in clause.tags:
                continue

            haystack = " ".join(
                [
                    clause.doc_title,
                    clause.quote,
                    clause.article_id,
                    " ".join(clause.obligations),
                    " ".join(clause.tags),
                ]
            )
            score = sum(1 for tok in tokens if tok in haystack)
            if score == 0:
                continue

            level_weight = -LEVEL_PRIORITY.get(clause.doc_type, 99)
            region_weight = 1 if region and clause.region == region else 0
            candidates.append(((score, region_weight, level_weight), clause))

        candidates.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in candidates[:top_k]]

    def answer_user_question(self, question: str, profile: dict[str, object]) -> str:
        """固定模板输出：结论-依据-建议-证据-补充信息。"""
        region = str(profile.get("region", ""))
        industry = str(profile.get("industry", ""))
        pollutant = str(profile.get("pollutant", ""))

        clauses = self.search_regulations(question, region=region or None, industry=industry or None, pollutant=pollutant or None)
        if len(clauses) < 2:
            return "未满足最小引用数（>=2）或未检索到有效条款，请补充地区/行业/危废场景信息。"

        legal_basis = [self._to_basis_line(c) for c in clauses]
        action_points = self._derive_action_points(clauses)
        evidence = self._derive_evidence_points(clauses)

        lines = [
            "【结论摘要】",
            "- 依据现行有效条款，当前场景一般需要落实‘分类贮存、规范标识、台账与联单一致、资质核验’。",
            "- 若所在省市存在更严地方要求，应按地方更严项执行。",
            "",
            "【适用依据（全国→地方）】",
        ]
        lines.extend(f"{i}. {item}" for i, item in enumerate(legal_basis, start=1))

        lines.extend(
            [
                "",
                "【合规建议（可执行清单）】",
                "- 必做项（高风险）：" + "；".join(action_points[:3]),
                "- 优化项（中低风险）：" + "；".join(action_points[3:5] or ["开展季度内审与培训复盘"]),
                "",
                "【证据链/台账清单】",
                "- " + "；".join(evidence),
                "",
                "【需要补充的信息】",
                "- 所在省/市、危废类别/代码、月产生量、暂存时长、转移单位资质核验情况。",
                "",
                "【风险与边界提示】",
                "- 本助手仅提供咨询评估建议，不构成法律裁决。",
                "- 涉及停产整治、重大违法或刑责边界事项，建议法务/第三方复核并与主管部门确认。",
            ]
        )
        return "\n".join(lines)

    def gap_analysis(self, profile: dict[str, object]) -> list[GapItem]:
        """危废5大场景问诊式评估。"""
        region = str(profile.get("region", ""))
        industry = str(profile.get("industry", ""))

        scenes = [
            ("危废判定/鉴别", bool(profile.get("has_hw_identification", False)), "危废代码/属性未明确"),
            ("暂存设施与现场规范", bool(profile.get("has_haz_waste_room", False)), "暂存设施或标识不完整"),
            ("转移联单与台账", bool(profile.get("has_transfer_manifest", False)), "联单与台账闭环不足"),
            ("制度与培训", bool(profile.get("has_training", False)), "岗位责任与培训记录缺失"),
            ("第三方处置核验", bool(profile.get("vendor_qualified", False)), "处置单位资质核验不足"),
        ]

        results: list[GapItem] = []
        for idx, (scene, ok, gap_text) in enumerate(scenes, start=1):
            if ok:
                continue
            refs = self.search_regulations(f"危废 {scene}", region=region or None, industry=industry or None, top_k=3)
            citations = [self._to_citation(c) for c in refs[:2]]
            results.append(
                GapItem(
                    scene=scene,
                    gap=gap_text,
                    risk_level="高" if idx <= 3 else "中",
                    plan_days=7 if idx == 1 else (30 if idx <= 4 else 90),
                    owner_role=["环保经理", "危废管理员", "台账管理员", "EHS经理", "采购/合规经理"][idx - 1],
                    actions=self._scene_actions(scene),
                    evidence_chain=self._scene_evidence(scene),
                    citations=citations,
                )
            )
        return results

    def generate_compliance_advice(self, profile: dict[str, object]) -> str:
        gaps = self.gap_analysis(profile)
        if not gaps:
            return "【结论摘要】当前危废管理基础项较完整，建议按季度复核制度-现场-台账一致性。"

        lines = ["【结论摘要】", "- 已识别危废管理差距项，建议按7/30/90天闭环整改。", "", "【Gap清单与整改计划】"]
        for i, g in enumerate(gaps, start=1):
            lines.extend(
                [
                    f"{i}. 场景：{g.scene}｜差距：{g.gap}｜风险：{g.risk_level}",
                    f"   - 计划：{g.plan_days}天；责任角色：{g.owner_role}",
                    f"   - 动作：{'；'.join(g.actions)}",
                    f"   - 证据：{'；'.join(g.evidence_chain)}",
                    f"   - 引用：{' | '.join(g.citations) if g.citations else '（需补充引用）'}",
                ]
            )

        lines.extend(
            [
                "",
                "【风控提示】",
                "- 任何关键结论均应对应引用条款；若引用不足，请先补检索再下结论。",
                "- 涉及行政处罚、停产整治、刑责边界，建议法务/第三方复核。",
            ]
        )
        return "\n".join(lines)

    def consulting_assessment_report(self, question: str, profile: dict[str, object]) -> RegulationSearchResult:
        clauses = self.search_regulations(question, region=str(profile.get("region", "")) or None, top_k=5)
        basis = [self._to_basis_line(c) for c in clauses[:5]]
        actions = self._derive_action_points(clauses)
        citations = [self._to_citation(c) for c in clauses[:5]]
        return RegulationSearchResult(
            summary="依据现行有效法规进行咨询评估：优先全国底线，地方更严从严执行。",
            applicability=f"地区={profile.get('region', '未提供')}；行业={profile.get('industry', '未提供')}",
            legal_basis=basis,
            action_points=actions,
            citations=citations,
            evidence_points=self._derive_evidence_points(clauses),
        )

    def _to_basis_line(self, c: RegulationClause) -> str:
        return (
            f"{c.doc_title}｜{c.doc_no}/{c.issuer}｜{c.status}｜{c.article_id}｜摘录：{c.quote[:25]}"
        )

    def _to_citation(self, c: RegulationClause) -> str:
        return f"{c.doc_title} {c.article_id}（{c.doc_no}，{c.issuer}，{c.source_url}）"

    def _derive_action_points(self, clauses: list[RegulationClause]) -> list[str]:
        points: list[str] = []
        for c in clauses:
            points.extend(c.obligations)
        uniq = list(dict.fromkeys(points))
        return uniq[:6] if uniq else ["补充条款检索后制定措施"]

    def _derive_evidence_points(self, clauses: list[RegulationClause]) -> list[str]:
        base = ["危废管理制度", "危废台账", "转移联单", "暂存间现场照片", "处置单位资质与合同"]
        if any("职业卫生" in c.tags or "职业卫生" in c.pollutant_factors for c in clauses):
            base.extend(["职业卫生检测报告", "职业健康培训记录"])
        return list(dict.fromkeys(base))

    def _scene_actions(self, scene: str) -> list[str]:
        mapping = {
            "危废判定/鉴别": ["梳理工艺产废点", "形成危废代码/属性清单", "建立年度管理计划"],
            "暂存设施与现场规范": ["完成防渗防雨与分区标识", "建立日巡检记录", "明确最长暂存时限"],
            "转移联单与台账": ["执行电子联单全流程", "台账与联单月度核对", "异常单据闭环整改"],
            "制度与培训": ["完善岗位职责", "组织年度培训与考试", "开展应急演练"],
            "第三方处置核验": ["核验资质有效期", "核对处置范围匹配", "保留合同与结算票据"],
        }
        return mapping[scene]

    def _scene_evidence(self, scene: str) -> list[str]:
        mapping = {
            "危废判定/鉴别": ["危废鉴别/判定记录", "危废代码清单"],
            "暂存设施与现场规范": ["暂存间照片", "标识清单", "巡检台账"],
            "转移联单与台账": ["转移联单", "出入库台账", "称重单据"],
            "制度与培训": ["制度文件", "培训签到/试卷", "应急演练记录"],
            "第三方处置核验": ["处置单位资质", "合同", "发票与结算单"],
        }
        return mapping[scene]

    def _tokenize(self, text: str) -> list[str]:
        raw = [tok for tok in re.split(r"[^\w\u4e00-\u9fff]+", text.lower().strip()) if tok]
        tokens: list[str] = []
        for tok in raw:
            if len(tok) < 2:
                continue
            tokens.append(tok)
            if re.search(r"[\u4e00-\u9fff]", tok) and len(tok) >= 4:
                tokens.extend(tok[i : i + 2] for i in range(len(tok) - 1))
        return list(dict.fromkeys(tokens))

    def _extract_tags(self, text: str) -> list[str]:
        candidates = ["危废", "台账", "转移", "标识", "监测", "排污许可", "职业卫生"]
        return [c for c in candidates if c in text]

    def _extract_pollutants(self, text: str) -> list[str]:
        keys = ["危废", "VOC", "COD", "氨氮", "颗粒物", "粉尘", "苯", "职业卫生"]
        return [k for k in keys if k in text]


if __name__ == "__main__":
    assistant = EnvironmentalConsultingAssistant()
    profile = {
        "region": "新疆",
        "industry": "石油化工",
        "has_hw_identification": False,
        "has_haz_waste_room": False,
        "has_transfer_manifest": False,
        "has_training": False,
        "vendor_qualified": False,
    }

    print(assistant.answer_user_question("危废暂存间要求和依据是什么？", profile))
    print("\n" + assistant.generate_compliance_advice(profile))
