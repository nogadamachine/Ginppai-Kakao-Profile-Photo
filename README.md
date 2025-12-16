# Ginppai-Kakao-Profile-Photo

macOS에서 실행 중인 **KakaoTalk Mac**의 캐시 데이터베이스(`Cache.db`)를  
**읽기 전용(read-only)** 으로 분석하여, 카카오 CDN에 캐시된 **프로필 이미지 리소스 URL**을 추출하고  
조건에 맞는 파일을 실제로 다운로드하는 CLI 도구입니다.

이 도구는 **카카오톡이 실행 중이며 DB가 실시간으로 업데이트되는(WAL 모드)** 환경을 고려하여 설계되었습니다.

---

## 주요 특징

- KakaoTalk Mac의 `Cache.db`를 **복사하지 않고 읽기 전용으로 접근**
- SQLite WAL 환경에서도 **일관된 스냅샷 기반 조회**
- `cfurl_cache_response` 테이블 기반 URL 분석
- 최신 요청 순(`time_stamp DESC`) 정렬
- 명확한 URL 필터링 규칙 적용 (프로필 이미지 중심)
- 다운로드 전 사용자 확인(y/n)
- 사람이 브라우저로 접근하는 패턴에 가까운 **안전한 기본 동작값**

---

## 동작 개요

1. KakaoTalk Mac의 `Cache.db`를 read-only 모드로 오픈
2. 조건에 맞는 CDN URL을 **실행 시점 기준으로 한 번만 조회**
3. 사용자에게 다운로드 여부 확인
4. 승인 시에만 다운로드 디렉터리 생성
5. 프로필 이미지 파일 다운로드 수행

---

## URL 필터링 규칙

### 포함 대상
- `https://p.kakaocdn.net/talkp/`
- `https://chat.kakaocdn.net/profile_resource/`

### 제외 대상
- `.jpg?*` (쿼리 스트링이 붙은 jpg)
- `*110x110_c.jpg` (썸네일 이미지)
- `.png`, `.png?*`

---

## 파일 저장 규칙

- 저장 경로:
  ```text
  downloads/YYYYMMDD_HHMMSS/
