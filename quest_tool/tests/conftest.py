"""pytest 공통 픽스처."""
import shutil
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def quest_xlsx_copy(tmp_path):
    """quests_test.xlsx 임시 복사본 경로 반환. 테스트 종료 후 자동 삭제."""
    src = FIXTURES / "quests_test.xlsx"
    dst = tmp_path / "quests_test.xlsx"
    shutil.copy(src, dst)
    return str(dst)
