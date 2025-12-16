# Ginppai-Kakao-Profile-Photo

macOS에서 실행 중인 **KakaoTalk Mac**의 캐시 데이터베이스(`Cache.db`)를  
**읽기 전용(Read-Only)** 으로 분석하여, 카카오 CDN에 캐시된 **프로필 이미지 리소스 URL**을 추출하고  
조건에 맞는 파일을 실제로 다운로드하는 CLI 도구입니다.

이 도구는 **카카오톡이 실행 중이며 DB가 실시간으로 갱신되는(SQLite WAL 모드)** 환경을 전제로 설계되었습니다.

---

## 프로젝트 목적

- KakaoTalk Mac 내부 캐시 구조 이해
- 프로필 이미지 CDN 리소스 분석
- 네트워크 후킹 없이 캐시 기반 데이터 수집
- 읽기 전용 접근을 통한 **낮은 위험도의 분석 도구 제공**

본 프로젝트는 자동화 수집 도구가 아닌,  
**분석·연구·교육·포렌식 목적**의 CLI 유틸리티입니다.

---

## 주요 특징

- `Cache.db` 파일 **복사 없이 직접 Read-Only 접근**
- SQLite WAL 환경에서도 **일관된 스냅샷 기반 조회**
- `cfurl_cache_response` 테이블 기반 URL 분석
- 최신 요청 순(`time_stamp DESC`) 정렬
- 프로필 이미지 중심의 명확한 URL 필터링
- 다운로드 전 사용자 확인(y/n)
- 사람의 브라우징 패턴에 가까운 **안전한 기본 동작값**
- 외부 라이브러리 없이 **Python 표준 라이브러리만 사용**

---

## 전체 동작 흐름

```
Cache.db (WAL)
   ↓ (read-only)
SQLite Snapshot
   ↓
URL Filter & Dedup
   ↓
User Confirm
   ↓
Download (safe defaults)
```

---

## URL 필터링 규칙

### 포함 대상
- https://p.kakaocdn.net/talkp/
- https://chat.kakaocdn.net/profile_resource/

### 제외 대상
- *.jpg?*
- *110x110_c.jpg
- *.png, *.png?*

---

## 파일 저장 규칙

- 저장 경로: downloads/YYYYMMDD_HHMMSS/
- 파일명 형식: sha1(url)_YYYYMMDD_HHMMSS.jpg

---

## 기본 동작 정책 (Safe by Default)

- 동시 다운로드 수: 2
- 요청 지연: 200~400ms (랜덤)
- User-Agent: macOS Safari

---

## 사용법

```bash
python3 kakao_cfurl_collect.py
python3 kakao_cfurl_collect.py --limit 200
```

---

## 요구 사항

- macOS
- Python 3.9 이상
- KakaoTalk Mac 설치됨

---

## 라이선스

MIT License

---

## 면책 조항

본 프로젝트는 비공식 도구이며,  
Kakao 또는 그 계열사와 어떠한 관계도 없습니다.
