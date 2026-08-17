import json
import re
from pathlib import Path
from typing import Dict, List, Any

class PolicyValidator:
    """
    台灣房產政策與法規反幻覺校驗引擎
    嚴格檢核生成內容中的貸款成數、寬限期、稅率、預售轉約限制及預告草案狀態
    """
    def __init__(self, knowledge_dir: Path):
        self.knowledge_dir = knowledge_dir
        self.policies = self._load_policies()
        self.terms = self._load_terms()

    def _load_policies(self) -> List[Dict[str, Any]]:
        path = self.knowledge_dir / "taiwan_policies.json"
        if not path.exists() or path.stat().st_size == 0:
            fallback = self.knowledge_dir.parent / "default_knowledge" / "taiwan_policies.json"
            if fallback.exists():
                path = fallback
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("policies", [])
            except Exception as e:
                print(f"[Validator] 載入法規庫失敗: {e}")
        return []

    def _load_terms(self) -> List[Dict[str, Any]]:
        path = self.knowledge_dir / "real_estate_terms.json"
        if not path.exists() or path.stat().st_size == 0:
            fallback = self.knowledge_dir.parent / "default_knowledge" / "real_estate_terms.json"
            if fallback.exists():
                path = fallback
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("terms", [])
            except Exception as e:
                print(f"[Validator] 載入術語庫失敗: {e}")
        return []

    def validate_content(self, content: str) -> Dict[str, Any]:
        """
        針對文案內容進行事實驗證與幻覺標記
        """
        warnings = []
        passed_checks = []
        applied_notes = []
        referenced_policies = []

        # 1. 檢核：央行第七波信用管制 (第二戶成數與寬限期)
        # 錯誤幻覺範例：第二戶宣稱可貸 6~8 成或享有寬限期
        if re.search(r"第[二2兩]戶.*?(?:貸[6789]|貸[6-9]0%|[6789]0%|享有寬限期|寬限期[1-5]年)", content):
            warnings.append("【高風險幻覺警示】偵測到提及「第二戶貸款可能大於5成或享有寬限期」。央行第七波管制下，自然人第二戶全台最高僅限 5 成且『無寬限期』(簽署1年內換屋切結者除外)。")
        elif "第二戶" in content or "信用管制" in content or "限貸" in content:
            passed_checks.append("符合央行第七波信用管制規範（第二戶最高5成/無寬限期）。")
            referenced_policies.append("中央銀行第七波選擇性信用管制")

        # 2. 檢核：新青安 3.0 貸款規範與轉租限制 (2026.08 生效)
        if "新青安" in content or "青年安心成家" in content or "青安" in content:
            if re.search(r"(買來出租|轉租賺租金|當包租公|投資客用新青安)", content):
                warnings.append("【法規違規警示】新青安 3.0 嚴禁出租與人頭代持！違者將被銀行追討利息補貼並重算貸款條件。")
            else:
                passed_checks.append("符合新青安 3.0 貸款規範（婚育加碼最高1500萬、排富200萬、自住專用、一生一次）。")
                referenced_policies.append("財政部青年安心成家購屋優惠貸款 3.0")

        # 3. 檢核：平均地權條例 (預售屋轉約換約禁止)
        if re.search(r"預售屋.*?(自由轉約|轉讓賺差價|隨時換約)", content):
            warnings.append("【重大違法警示】平均地權條例已全面禁止預售屋換約轉售（除二親等及特殊核准除外），最高可處5000萬罰鍰。")
        elif "預售屋" in content and ("換約" in content or "轉讓" in content):
            passed_checks.append("符合平均地權條例預售屋轉售限制。")
            referenced_policies.append("平均地權條例修正案")

        # 4. 檢核：預告草案標示（如虛坪改革、國土計畫法）
        if "虛坪改革" in content or "公設比改革" in content:
            if not any(k in content for k in ["草案", "預告", "研議", "尚未實施", "推動中"]):
                warnings.append("【時空錯亂警示】「虛坪改革方案」目前為內政部預告與研議草案，尚未修法三讀實施，文案應明確標註『預告草案』，不可宣稱已強制上路。")
                applied_notes.append("已提示虛坪改革為預告草案階段。")
            else:
                passed_checks.append("已正確將虛坪改革標註為「預告草案/研議推動中」。")
                referenced_policies.append("內政部虛坪改革方案（預告草案）")

        # 5. 檢核：房地合一稅 2.0 短期稅率
        if re.search(r"[12]年內出售.*?(免稅|只要[12]0%|低稅率)", content):
            warnings.append("【稅務錯誤警示】持有2年內出售房地合一稅率為 45%，5年內為 35%，不可誤導免稅或低稅率。")

        # 6. 檢核：雨遮計價
        if re.search(r"(新建案|預售|新成屋).*?雨遮.*?計價", content):
            warnings.append("【坪數計價警示】2018年後取得建照之新建物，雨遮全面「不計坪、不計價」。")

        return {
            "is_valid": len(warnings) == 0,
            "warning_count": len(warnings),
            "warnings": warnings,
            "passed_checks": passed_checks,
            "applied_notes": applied_notes,
            "referenced_policies": list(set(referenced_policies))
        }

    def get_grounding_context(self, topic: str = "") -> str:
        """
        提供 LLM 的最新真實法規與防幻覺 Prompt 注入文字
        """
        policy_lines = []
        for p in self.policies:
            policy_lines.append(f"【{p.get('title')}】（狀態：{p.get('status')} / 生效主管機關：{p.get('authority')}）")
            for r in p.get("key_rules", []):
                policy_lines.append(f" - {r}")
            if p.get("warning_notice"):
                policy_lines.append(f" - 重要宣導：{p.get('warning_notice')}")
            policy_lines.append(f" - 防幻覺底線：{p.get('anti_hallucination_guideline')}")
            policy_lines.append("")
        return "\n".join(policy_lines)
