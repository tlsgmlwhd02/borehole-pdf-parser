# borehole-pdf-parser

한국 시추주상도 PDF에서 풍화암/연암/경암 상면 심도를 자동으로 추출하는 도구입니다.

## 설치

```bash
pip install pdfplumber
```

## 사용법

```bash
python parse_borehole.py 시추주상도.pdf
```

여러 PDF 한번에 처리:
```bash
for f in *.pdf; do python parse_borehole.py "$f"; done
```

결과 합치기 (중복 제거):
```bash
python3 << 'EOF'
import csv, glob
output_file = 'all_boreholes.csv'
all_rows = []
fieldnames = None
for csv_file in glob.glob('*_parsed.csv'):
    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        if fieldnames is None:
            fieldnames = reader.fieldnames
        for row in reader:
            all_rows.append(row)
seen = set()
unique_rows = []
for row in all_rows:
    bid = row.get('borehole_id')
    if bid not in seen:
        unique_rows.append(row)
        seen.add(bid)
with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(unique_rows)
    print(f"총 {len(unique_rows)}개 시추공 저장")
EOF
```

## 출력 CSV 컬럼

| 컬럼 | 설명 |
|------|------|
| borehole_id | 시추공 번호 |
| X_N | X 좌표 (TM 중부원점) |
| Y_E | Y 좌표 (TM 중부원점) |
| elevation | 지표고 (m) |
| WR_depth | 풍화암 상면 심도 (GL-m) |
| SR_depth | 연암 상면 심도 (GL-m) |
| HR_depth | 경암 상면 심도 (GL-m) |

## 지원 형식

국토지반정보 포털 등에서 다운받은 한국 표준 시추주상도 PDF
