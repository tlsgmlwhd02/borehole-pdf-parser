"""
시추주상도 PDF 파싱 스크립트
-------------------------------
풍화암 / 연암 / 경암 상면 심도를 자동 추출하여 CSV로 저장합니다.

사용법:
    pip install pdfplumber
    python parse_borehole.py 주상도.pdf
    python parse_borehole.py 주상도.pdf --output 결과.csv
    python parse_borehole.py 주상도.pdf --verbose

출력 CSV 컬럼:
    borehole_id, X_N, Y_E, elevation,
    WR_depth (풍화암 top, GL-m),
    SR_depth (연암 top, GL-m),
    HR_depth (경암 top, GL-m),
    WR_elev  (풍화암 top 표고 = elevation - WR_depth),
    SR_elev  (연암 top 표고),
    HR_elev  (경암 top 표고)
"""

import re
import csv
import sys
import argparse
from pathlib import Path

try:
    import pdfplumber
except ImportError:
    print("[오류] pdfplumber가 설치되지 않았습니다.")
    print("  pip install pdfplumber  명령어로 설치하세요.")
    sys.exit(1)


# ─── 지반명 키워드 ────────────────────────────────────────────────
LAYER_KEYWORDS = ['매립토', '퇴적토', '풍화토', '풍화암', '연암', '경암']
DEPTH_LINE_PAT = re.compile(r'^(\d+(?:\.\d+)?)\s+\d+(?:\.\d+)?\s+\d+(?:\.\d+)?')


def parse_page(lines: list[str], bh: dict) -> None:
    """한 페이지의 라인 목록을 받아 bh dict를 업데이트합니다."""
    for i, line in enumerate(lines):
        for keyword in LAYER_KEYWORDS:
            if keyword + '층' not in line:
                continue
            # 현재 라인 위쪽 최대 6줄에서 심도 라인 역방향 탐색
            for j in range(i - 1, max(i - 7, -1), -1):
                m = DEPTH_LINE_PAT.match(lines[j])
                if m:
                    depth_val = float(m.group(1))
                    if keyword == '풍화암' and bh['WR_depth'] is None:
                        bh['WR_depth'] = depth_val
                    elif keyword == '연암' and bh['SR_depth'] is None:
                        bh['SR_depth'] = depth_val
                    elif keyword == '경암' and bh['HR_depth'] is None:
                        bh['HR_depth'] = depth_val
                    break


def parse_pdf(pdf_path: str, verbose: bool = False) -> list[dict]:
    """PDF 전체를 파싱하여 시추공별 결과 리스트를 반환합니다."""
    boreholes: dict[str, dict] = {}

    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text()
            if not text:
                continue
            lines = text.split('\n')

            # ── 헤더 파싱 ──────────────────────────────────────────
            bh_id = x_coord = y_coord = elev = None

            for line in lines:
                if m := re.search(r'시추번호\s+([\w\-]+)', line):
                    bh_id = m.group(1)
                if m := re.search(r'X\(N\):\s*([\d.]+)', line):
                    x_coord = float(m.group(1))
                if m := re.search(r'Y\(E\):\s*([\d.]+)', line):
                    y_coord = float(m.group(1))
                if m := re.search(r'위치.+?\s+([\d.]+)\s*$', line):
                    elev = float(m.group(1))

            if not bh_id:
                continue

            # 새 시추공이면 초기화
            if bh_id not in boreholes:
                boreholes[bh_id] = {
                    'borehole_id': bh_id,
                    'X_N': x_coord,
                    'Y_E': y_coord,
                    'elevation': elev,
                    'WR_depth': None,   # 풍화암 top (GL-m)
                    'SR_depth': None,   # 연암 top (GL-m)
                    'HR_depth': None,   # 경암 top (GL-m)
                }
            else:
                # 좌표/표고 누락 보완
                bh = boreholes[bh_id]
                if bh['X_N'] is None and x_coord: bh['X_N'] = x_coord
                if bh['Y_E'] is None and y_coord: bh['Y_E'] = y_coord
                if bh['elevation'] is None and elev: bh['elevation'] = elev

            # ── 지층 파싱 ─────────────────────────────────────────
            parse_page(lines, boreholes[bh_id])

            if verbose:
                print(f"  [{page_num:4d}/{total}] {bh_id}  "
                      f"WR={boreholes[bh_id]['WR_depth']}  "
                      f"SR={boreholes[bh_id]['SR_depth']}  "
                      f"HR={boreholes[bh_id]['HR_depth']}")

    # ── 표고 계산 ─────────────────────────────────────────────────
    results = []
    for bh in boreholes.values():
        elev = bh['elevation']
        for layer, key in [('WR', 'WR_depth'), ('SR', 'SR_depth'), ('HR', 'HR_depth')]:
            d = bh[key]
            bh[f'{layer}_elev'] = round(elev - d, 2) if (elev and d is not None) else None
        results.append(bh)

    return results


def save_csv(results: list[dict], output_path: str) -> None:
    fieldnames = [
        'borehole_id', 'X_N', 'Y_E', 'elevation',
        'WR_depth', 'SR_depth', 'HR_depth',
        'WR_elev', 'SR_elev', 'HR_elev',
    ]
    with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(results)
    print(f"\n✅ CSV 저장 완료: {output_path}  ({len(results)}개 시추공)")


def print_summary(results: list[dict]) -> None:
    print(f"\n{'='*65}")
    print(f"{'시추번호':<12} {'X(N)':>12} {'Y(E)':>12} "
          f"{'WR(m)':>7} {'SR(m)':>7} {'HR(m)':>7}")
    print(f"{'-'*65}")
    for r in results:
        wr = f"{r['WR_depth']:.1f}" if r['WR_depth'] is not None else '  -'
        sr = f"{r['SR_depth']:.1f}" if r['SR_depth'] is not None else '  -'
        hr = f"{r['HR_depth']:.1f}" if r['HR_depth'] is not None else '  -'
        print(f"{r['borehole_id']:<12} {r['X_N'] or '-':>12} {r['Y_E'] or '-':>12} "
              f"{wr:>7} {sr:>7} {hr:>7}")
    none_wr = sum(1 for r in results if r['WR_depth'] is None)
    none_sr = sum(1 for r in results if r['SR_depth'] is None)
    print(f"\n총 {len(results)}개 공  |  풍화암 미검출: {none_wr}  연암 미검출: {none_sr}")


def main():
    parser = argparse.ArgumentParser(description='시추주상도 PDF → CSV 파싱')
    parser.add_argument('pdf', help='입력 PDF 파일 경로')
    parser.add_argument('--output', '-o', help='출력 CSV 파일 경로 (기본: 입력파일명.csv)')
    parser.add_argument('--verbose', '-v', action='store_true', help='페이지별 진행 상황 출력')
    args = parser.parse_args()

    if not Path(args.pdf).exists():
        print(f"[오류] 파일을 찾을 수 없습니다: {args.pdf}")
        sys.exit(1)

    out = args.output or Path(args.pdf).stem + '_parsed.csv'

    print(f"📄 PDF 파싱 중: {args.pdf}")
    results = parse_pdf(args.pdf, verbose=args.verbose)

    print_summary(results)
    save_csv(results, out)


if __name__ == '__main__':
    main()
