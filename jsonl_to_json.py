import json
import os

import json
import os

# JSONL 파일을 개별 JSON 파일로 분리하는 함수
def split_jsonl(input_file, output_dir):
    # 출력 디렉토리가 존재하지 않으면 생성
    os.makedirs(output_dir, exist_ok=True)
    
    # JSONL 파일 읽기
    with open(input_file, 'r', encoding='utf-8') as file:
        for line in file:
            # 각 라인을 JSON 형식으로 변환
            data = json.loads(line.strip())
            
            # "image_id" 필드를 파일 이름으로 사용
            image_id = data.get("image_id")
            if not image_id:
                print("Missing 'image_id' in line:", line)
                continue
            
            # "image_id"가 ".tif"로 끝나면 확장자 제거
            if image_id.endswith('.tif'):
                image_id = image_id[:-4]
            
            # 개별 JSON 파일로 저장
            output_file = os.path.join(output_dir, f"{image_id}.json")
            with open(output_file, 'w', encoding='utf-8') as json_file:
                json.dump(data, json_file, ensure_ascii=False, indent=4)
                
if __name__ == "__main__":
    input_file = '/Users/kingsfavor/Desktop/PARTTIME/220v/data/jsonl/output.jsonl'
    output_dir = '/Users/kingsfavor/Desktop/PARTTIME/220v/data/json'
    split_jsonl(input_file, output_dir)
