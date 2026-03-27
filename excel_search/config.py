"""
config.py - config.txt 파싱 및 저장 모듈
"""

from pathlib import Path


def load_config(config_path: str = "config.txt") -> dict:
    """
    config.txt를 파싱하여 설정값을 dict로 반환한다.

    Args:
        config_path: 설정 파일 경로 (기본값: "config.txt")

    Returns:
        {
            "excel_folder": str,        # 폴더 경로 (없으면 빈 문자열)
            "exclude_files": list[str]  # 제외 파일명 리스트 (없으면 빈 리스트)
        }
    """
    # 기본값 정의 - 파일이 없거나 키가 없을 때 사용
    default: dict = {
        "excel_folder": "",
        "exclude_files": [],
    }

    path = Path(config_path)

    # 파일이 없으면 예외 없이 기본값 반환
    if not path.exists():
        return default

    raw: dict[str, str] = {}

    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            # 빈 줄 또는 주석(#으로 시작) 무시
            if not line or line.startswith("#"):
                continue

            # KEY=VALUE 형식만 처리
            if "=" not in line:
                continue

            key, _, value = line.partition("=")
            raw[key.strip()] = value.strip()

    # EXCEL_FOLDER 파싱
    excel_folder = raw.get("EXCEL_FOLDER", "")

    # EXCLUDE_FILES 파싱: 쉼표로 split 후 각 항목 strip, 빈 문자열 제거
    exclude_raw = raw.get("EXCLUDE_FILES", "")
    if exclude_raw:
        exclude_files = [item.strip() for item in exclude_raw.split(",") if item.strip()]
    else:
        exclude_files = []

    return {
        "excel_folder": excel_folder,
        "exclude_files": exclude_files,
    }


def save_config(config: dict, config_path: str = "config.txt") -> None:
    """
    설정 dict를 config.txt 형식으로 저장한다.

    Args:
        config:      저장할 설정 dict
        config_path: 저장할 파일 경로 (기본값: "config.txt")
    """
    path = Path(config_path)

    # 부모 디렉토리가 없으면 생성
    path.parent.mkdir(parents=True, exist_ok=True)

    excel_folder: str = config.get("excel_folder", "")
    exclude_files: list[str] = config.get("exclude_files", [])

    # 제외 파일 목록을 "파일1.xlsx, 파일2.xlsx" 형식으로 join
    exclude_value = ", ".join(exclude_files)

    lines = [
        "# 엑셀 파일이 있는 폴더 경로",
        f"EXCEL_FOLDER={excel_folder}",
        "",
        "# 검색 제외 파일 목록 (쉼표로 구분, 파일명만 기재)",
        f"EXCLUDE_FILES={exclude_value}",
        "",  # 파일 끝 개행
    ]

    # pathlib.Path로 파일 저장
    path.write_text("\n".join(lines), encoding="utf-8")
