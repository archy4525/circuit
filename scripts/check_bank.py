"""檢查題庫是否完整，並用公式重算數值題。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from circuit_game.bank import BankError, load_bank


def main() -> int:
    try:
        bank = load_bank()
    except BankError as exc:
        print("題庫檢查沒有通過：")
        for item in exc.errors:
            print(f"- {item}")
        return 1
    print(
        f"題庫檢查通過：{len(bank.templates)} 種題型，"
        f"{len(bank.questions)} 題固定題，{len(bank.topics)} 個主題，{len(bank.sources)} 個來源。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
