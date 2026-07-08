# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 개발 원칙

1. **모르면 멈추고 물어본다** — 불명확하거나 해석이 갈리는 부분은 가정하지 않고 사용자에게 선택지를 제시한 뒤 확인 후 진행
2. **최소한의 코드** — 추측성 코드, 미리 대비하는 코드 금지. 지금 필요한 것만 구현
3. **수정은 꼭 필요한 곳만** — 기능 추가·수정 시 관련 없는 코드는 건드리지 않음
4. **명확한 성공 기준** — 구현 전 완료 기준을 먼저 정의하고, 기준 충족까지 테스트 반복

## 프로젝트 개요

**SL MYO SI** — 하루를 시작하기 전 딱 한 곳에서 날씨·뉴스·읽을거리를 챙겨보는 모닝 대시보드.  
타겟: 10~30대 (학생, 젊은 직장인, 커플·부부).

## 기술 스택

| 역할 | 선택 |
|---|---|
| 앱 프레임워크 | Streamlit (Python) |
| AI 콘텐츠 생성 | Claude API (Anthropic) |
| 날씨 | 기상청 API + OpenWeatherMap |
| 뉴스 | 네이버 뉴스 RSS |
| 이력 저장 | JSON 파일 |
| 배포 | Streamlit Community Cloud |

## 실행 명령

```bash
pip install streamlit anthropic requests
streamlit run app.py
```

## 콘텐츠 구조

섹션은 아래 순서로 단일 페이지에 배치. PC는 뉴스만 2열 그리드, 나머지는 전체폭. 모바일은 전체 1열.

1. **날씨** — 기상청 + OpenWeatherMap 2개 소스 교차 수집. 체감온도·강수확률·미세먼지 포함
2. **뉴스** 
3. **문학·철학 글귀** — Claude API 생성. 책 발췌·인물 기록·사자성어 중 매일 1편, 500자 이상, 한국어 전용

## AI 생성 콘텐츠 공통 규칙

- 모든 출력은 **한국어**로만
- 생성 이력을 JSON 파일에 저장해 동일 주제·인물·사자성어 재출력 방지
- 글귀: 책 제목·저자 또는 인물 소개 반드시 포함
