# cctv-server

deep-cctv의 서버이다.

## 개요

cctv client 에서 보낸 영상을 저장한다. ai 모델을 사용해 영상을 분석한다. 이상 유무와 실시간 영상을 관리자 페이지에 서빙한다.

## 실행

### 개발 환경

```bash
pip install -r requirements.txt
```

### 배포 환경

```bash
docker build . -t cctv-server
docker run -p 80:80 cctv-server -v /path/to/save:/code/app/storage
```

## 개발

- fastapi
- tensorflow
- opencv
- pydantic
