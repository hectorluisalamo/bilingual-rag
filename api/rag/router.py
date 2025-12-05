import json, re, os
from typing import List, Dict, Optional
from rapidfuzz import process, fuzz

INJECTION = re.compile(r"ignore previous|system prompt|do anything now", re.I)

class FAQRouter:
    def __init__(self, path: Optional[str]):
        self.items: List[Dict] = []
        self.norm_to_idx: Dict[str, int] = {}
        if path and os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    obj = json.loads(line)
                    self.items.append(obj)
                    self.norm_to_idx[self._norm(obj.get("q",""))] = len(self.items)-1

    def _norm(self, s: str) -> str:
        s = s or ""
        s = s.strip().lower()
        s = re.sub(r"\s+", " ", s)
        return s

    def route(self, query: str, lang_pref: List[str]) -> Optional[Dict]:
        if INJECTION.search(query):
            return "rag", "guarded"
        if not self.items:
            return None
        qn = self._norm(query)
        # Exact/canonical match
        if qn in self.norm_to_idx:
            it = self.items[self.norm_to_idx[qn]]
            if not lang_pref or it.get("lang") in lang_pref:
                return {"route":"faq","answer":it.get("a",""),"citations":[{"uri":it.get("uri",""),"snippet":it.get("a","")}]}
        # Fuzzy top-1 within language preference
        choices = [(i, it["q"]) for i,it in enumerate(self.items) if not lang_pref or it.get("lang") in lang_pref]
        if not choices:
            return None
        idxs, texts = zip(*choices)
        best = process.extractOne(qn, texts, scorer=fuzz.token_sort_ratio)
        if best and best[1] >= 90:
            it = self.items[idxs[best[2]]]
            return {"route":"faq","answer":it.get("a",""),"citations":[{"uri":it.get("uri",""),"snippet":it.get("a","")}]}
        return None

def load_faq(path: Optional[str]) -> FAQRouter:
    return FAQRouter(path)
