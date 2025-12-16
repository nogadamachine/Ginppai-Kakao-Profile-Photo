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

본 프로젝트는 자동화 수집 도구가 아닌  
**분석·연구·교육·포렌식 목적**의 CLI 유틸리티입니다.

---

## 주요 특징

- `Cache.db` 파일 **복사 없이 직접 Read-Only 접근**
- SQLite WAL 환경에서도 **일관된 스냅샷 기반 조회**
- `cfurl_cache_response` 테이블 기반 URL 분석
- 최신 요청 순(`time_stamp DESC`) 정렬
- 프로필 이미지 중심의 명확한 URL 필터링
- 다운로드 전 사용자 확인(y/n)
- 사람이 브라우저로 접근하는 패턴에 가까운 **안전한 기본 동작값**
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

## 파일 저장 규칙

- 저장 경로  
  `downloads/YYYYMMDD_HHMMSS/`

- 파일명 형식  
  `{sha1(url)}_{YYYYMMDD_HHMMSS}.jpg`

---

## 기본 동작 정책 (Safe by Default)

옵션을 전혀 지정하지 않아도 **안전한 동작을 기본값으로 보장**합니다.

- 동시 다운로드 수: **2**
- 요청 지연: **200 ~ 400ms (랜덤)**
- User-Agent: **macOS Safari**
- CDN/WAF 자동화 탐지 리스크 최소화

---

## 요구 사항

- macOS
- Python 3.9 이상
- KakaoTalk Mac 설치 및 실행 이력 존재

---

## 설치

```bash
git clone https://github.com/nogadamachine/Ginppai-Kakao-Profile-Photo.git
cd Ginppai-Kakao-Profile-Photo
```

---

## 사용법

### 기본 실행 (권장)

macOS용 PC카톡에서 추출하고 싶은 사람의 카카오톡 프로필 사진을 확인한 후
```bash
python3 ginppai.py
```
### 주요 옵션 전체 목록

| 옵션 | 설명 |
|---|---|
| `--db PATH` | 분석할 Cache.db 경로 (기본값: KakaoTalk Mac 기본 경로) |
| `--limit N` | 최신 N개의 URL만 처리 |
| `--downloads-dir PATH` | 다운로드 루트 디렉터리 |
| `--concurrency N` | 동시 다운로드 수 (기본값: 2) |
| `--delay-ms MS` | 각 요청 전 기본 지연(ms) |
| `--delay-jitter-ms MS` | 랜덤 지연 범위(ms) |
| `--timeout-sec SEC` | 다운로드 요청 타임아웃 |
| `--max-bytes N` | 파일 최대 크기 제한 (0 이하 시 제한 없음) |
| `--user-agent UA` | HTTP User-Agent 문자열 |
| `--sqlite-timeout-ms MS` | SQLite busy timeout |
| `--db-retries N` | DB 읽기 재시도 횟수 |
| `--db-retry-sleep-ms MS` | DB 재시도 간 대기 시간 |
| `--immutable` | SQLite immutable 모드 (DB 변경 없을 때만 사용 권장) |

---

## 변경 이력

### [0.1.0] 최초 공개 버전

- KakaoTalk Mac `Cache.db` 읽기 전용 분석
- WAL 환경 대응(SQLite busy timeout + 재시도)
- 프로필 이미지 CDN URL 추출
- 결정적 파일명 규칙 적용
- 안전한 기본 다운로드 설정
- 사용자 확인 후 다운로드 진행
- 실행 단위 디렉터리 격리

---

## 의도적으로 하지 않는 것들

- 인증 우회
- 암호화 해제
- KakaoTalk 데이터 변경
- 상시 백그라운드 수집
- 공격적 트래픽 생성

---

## 사용 목적 및 책임

- 개인 분석
- 캐시 구조 연구
- 교육·포렌식 목적

본 도구의 사용으로 발생하는 모든 법적 책임은 사용자 본인에게 있습니다.  
본 프로젝트는 **비공식 도구**이며 Kakao 또는 그 계열사와 어떠한 관계도 없습니다.
