import streamlit as st
import requests
import json
import re
import html as _html
import time
import os
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from urllib.parse import urlparse

st.set_page_config(page_title="SL MYO SI", layout="wide")

# def get_greeting():
#     hour = datetime.now(ZoneInfo("Asia/Seoul")).hour
#     if 0 <= hour < 6:
#         return "늦게까지 뭐 하고 계세요?  \n얼른 주무세요 😴"
#     elif 6 <= hour < 9:
#         return "굿모닝!  \n오늘도 좋은 하루 시작해봐요 🌅"
#     elif 9 <= hour < 12:
#         return "오전도 힘차게!  \n오늘 하루 잘 부탁해요 ☀️"
#     elif 12 <= hour < 14:
#         return "점심은 드셨나요?  \n잘 챙겨 드세요! 🍱"
#     elif 14 <= hour < 18:
#         return "오후도 파이팅!  \n조금만 더 힘내봐요 ☕"
#     elif 18 <= hour < 21:
#         return "오늘 하루도 수고했어요.  \n잠깐 쉬어가요 🌆"
#     else:
#         return "오늘 하루 어땠나요?  \n내일도 잘 부탁해요 🌙"

# st.title(get_greeting())
st.markdown(
    """
    <style>
    div[data-testid='stMarkdownContainer'] a { white-space: normal !important; overflow: visible !important; text-overflow: clip !important; }
    div[data-testid='stMarkdownContainer'] p { overflow: visible !important; }

    :root {
        --ink: #1b1b1f;
        --line: #ececef;
        --chip-bg: #f2f2f3;
    }

    html, body, [class*="css"] {
        font-family: "Segoe UI", ui-sans-serif, system-ui, sans-serif;
    }
    h1, h2, h3 {
        font-family: "Century Gothic", "Poppins", "Futura", ui-sans-serif, sans-serif;
        letter-spacing: -0.01em;
    }
    [data-testid="stAppViewContainer"] h1 { font-weight: 800; color: var(--ink); font-size: 1.5rem; }
    [data-testid="stAppViewContainer"] h2 { font-size: 1.25rem; }
    [data-testid="stAppViewContainer"] h3 { font-size: 1.05rem; }

    /* 키워드 칩 (버튼) */
    .st-key-kw_buttons div[data-testid="stButton"] button {
        border-radius: 8px;
        border: none;
        background: var(--chip-bg);
        color: var(--ink);
        font-weight: 600;
        font-size: 0.85em;
        padding: 3px 12px;
    }
    .st-key-kw_buttons div[data-testid="stButton"] button[kind="primary"] {
        background: var(--ink);
        color: #fff;
    }

    /* 관련뉴스 키워드(아코디언 제목) 강조 */
    .st-key-news_section details[data-testid="stExpander"] summary p {
        font-size: 1.8em;
        font-weight: 700;
    }

    hr {
        border: none;
        border-top: 4px solid #e8e8eb !important;
        margin: 28px -16px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

OUTLET_NAMES = {
    "yna.co.kr": "연합뉴스", "newsis.com": "뉴시스", "news1.kr": "뉴스1",
    "kbs.co.kr": "KBS", "imnews.imbc.com": "MBC", "mbc.co.kr": "MBC",
    "sbs.co.kr": "SBS", "ytn.co.kr": "YTN", "jtbc.co.kr": "JTBC",
    "tvchosun.com": "TV조선", "mbn.co.kr": "MBN", "ichannela.com": "채널A",
    "chosun.com": "조선일보", "joongang.co.kr": "중앙일보", "donga.com": "동아일보",
    "hani.co.kr": "한겨레", "khan.co.kr": "경향신문", "hankookilbo.com": "한국일보",
    "mk.co.kr": "매일경제", "hankyung.com": "한국경제", "sedaily.com": "서울경제",
    "mt.co.kr": "머니투데이", "edaily.co.kr": "이데일리", "asiae.co.kr": "아시아경제",
    "heraldcorp.com": "헤럴드경제", "fnnews.com": "파이낸셜뉴스",
}

def _outlet_name(url):
    host = urlparse(url).netloc.lower()
    for domain, name in OUTLET_NAMES.items():
        if domain in host:
            return name
    return host

# ── Claude API 직접 호출 ──────────────────────────
_session = requests.Session()
_session.trust_env = False  # 시스템 프록시 설정 무시 (한국어 자격증명 인코딩 오류 방지)

def call_claude(prompt, max_tokens=1500):
    body = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }, ensure_ascii=False).encode("utf-8")

    r = _session.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": st.secrets["ANTHROPIC_API_KEY"],
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        data=body,
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["content"][0]["text"]

# ── AI 콘텐츠 캐시·이력 ───────────────────────────
DAILY_FILE = "daily_content.json"
CONTENT_HISTORY_FILE = "content_history.json"

def load_daily(key, refresh_date):
    """오늘 날짜로 저장된 콘텐츠 반환, 없으면 None"""
    if not os.path.exists(DAILY_FILE):
        return None
    with open(DAILY_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    entry = data.get(key, {})
    return entry.get("content") if entry.get("date") == refresh_date else None

def save_daily(key, refresh_date, content):
    data = {}
    if os.path.exists(DAILY_FILE):
        with open(DAILY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    data[key] = {"date": refresh_date, "content": content}
    with open(DAILY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_content_history(section):
    if not os.path.exists(CONTENT_HISTORY_FILE):
        return []
    with open(CONTENT_HISTORY_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get(section, [])

def save_content_history(section, topic):
    data = {}
    if os.path.exists(CONTENT_HISTORY_FILE):
        with open(CONTENT_HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    topics = data.get(section, [])
    topics.append(topic)
    data[section] = topics[-30:]
    with open(CONTENT_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ── 공통 유틸 ──────────────────────────────────────
def get_refresh_date():
    """한국시간 오전 6시 기준 갱신 날짜 반환"""
    now = datetime.now(ZoneInfo("Asia/Seoul"))
    if now.hour < 6:
        return (now - timedelta(days=1)).strftime("%Y-%m-%d")
    return now.strftime("%Y-%m-%d")

# ── 뉴스 함수 ──────────────────────────────────────
def _clean_title(title):
    return _html.unescape(re.sub(r"<[^>]+>", "", title))


# ══════════════════════════════════════════════════
# 뉴스
# ══════════════════════════════════════════════════
refresh_date = get_refresh_date()

# ── 공통: 기사 풀 수집 ────────────────────────────
# 2개 쿼리 × 10페이지 = 최대 2000개 제목, 페이지별로 저장
@st.cache_data(ttl=86400)
def fetch_discovery_pool(refresh_date):
    queries = ["정치 사회 사건", "연예 문화 스포츠"]
    titles = []
    for query in queries:
        for page_idx in range(10):
            try:
                r = _session.get(
                    "https://openapi.naver.com/v1/search/news.json",
                    headers={
                        "X-Naver-Client-Id": st.secrets["NAVER_CLIENT_ID"],
                        "X-Naver-Client-Secret": st.secrets["NAVER_CLIENT_SECRET"],
                    },
                    params={"query": query, "display": 100, "start": page_idx * 100 + 1, "sort": "date"},
                    timeout=10,
                )
                r.raise_for_status()
                items = r.json()["items"]
                titles.extend(_clean_title(i["title"]) for i in items)
                time.sleep(0.25)
                if len(items) < 100:
                    break
            except Exception:
                break
    return titles


@st.cache_data(ttl=86400)
def fetch_related_news(keyword, refresh_date, display=5):
    try:
        r = _session.get(
            "https://openapi.naver.com/v1/search/news.json",
            headers={
                "X-Naver-Client-Id": st.secrets["NAVER_CLIENT_ID"],
                "X-Naver-Client-Secret": st.secrets["NAVER_CLIENT_SECRET"],
            },
            params={"query": keyword, "display": display, "sort": "sim"},
            timeout=10,
        )
        r.raise_for_status()
        return r.json()["items"]
    except Exception:
        return []

def _parse_kw(text):
    m = re.search(r"\[.*?\]", text, re.DOTALL)
    if not m:
        return []
    try:
        return json.loads(m.group())
    except Exception:
        return []

with st.container(key="news_section"):
    st.header("슬쩍 인기뉴스")

    # ── 오늘의 인기토픽 ───────────────────────────────
    cached_kw = load_daily("news_classified", refresh_date)
    if cached_kw:
        kw_list = json.loads(cached_kw)
    else:
        with st.spinner("기사 수집 중 (최대 60초)..."):
            pool = fetch_discovery_pool(refresh_date)
        with st.spinner("인기토픽 분석 중..."):
            prompt_kw = f"""다음은 최근 6-12시간 동안의 한국 뉴스 기사 제목들입니다.
단순 속보가 아닌, 여러 시간에 걸쳐 반복적으로 다뤄진 핵심 화제 키워드 10개를 추출하세요.
네이버에서 검색하면 관련 기사가 많이 나올 구체적인 키워드여야 합니다.

{chr(10).join(pool[:400])}

JSON 배열만 출력: ["키워드1", "키워드2"]"""
            kw_list = _parse_kw(call_claude(prompt_kw, max_tokens=400))
        save_daily("news_classified", refresh_date, json.dumps(kw_list, ensure_ascii=False))
        save_daily("news_classified_time", refresh_date, datetime.now(ZoneInfo("Asia/Seoul")).strftime("%y/%m/%d %H:%M"))

    kw_time = load_daily("news_classified_time", refresh_date) or ""

    if "selected_kw" not in st.session_state:
        st.session_state.selected_kw = None

    st.subheader("화제키워드")
    with st.container(key="kw_buttons", horizontal=True, gap="xsmall"):
        for kw in kw_list:
            is_selected = st.session_state.selected_kw == kw
            if st.button(kw, key=f"kwbtn_{kw}", type="primary" if is_selected else "secondary"):
                st.session_state.selected_kw = None if is_selected else kw
    st.caption(f"기준 시각: {kw_time}" if kw_time else f"기준일: {refresh_date}")

    st.subheader("관련뉴스")

    for kw in kw_list:
        with st.expander(kw, expanded=(kw == st.session_state.selected_kw)):
            articles = fetch_related_news(kw, refresh_date, display=5)
            for art in articles:
                title = _clean_title(art["title"])
                link = art.get("originallink") or art.get("link", "")
                outlet = _outlet_name(link)
                st.markdown(f"[{title}]({link})  \n<small>{outlet}</small>", unsafe_allow_html=True)

st.divider()

# ══════════════════════════════════════════════════
# 문학·철학 글귀
# ══════════════════════════════════════════════════
LITERARY_TYPE_GUIDE = {
    "책 발췌": "책 발췌: 유명 소설·자기개발서·시집·과학도서의 인상적인 문단 → 책 제목, 저자 포함",
    "인물 기록": "인물 기록: 유명인의 연설·인터뷰·사고방식 → 인물 소개 포함",
    "사자성어": "사자성어: 반드시 4글자 한자어로 된 사자성어만 선택. 한자 원문, 뜻풀이, 유래 고사 순으로",
}

def _pick_literary_type():
    last_type = (load_content_history("literary_type") or [None])[-1]
    candidates = [t for t in LITERARY_TYPE_GUIDE if t != last_type]
    return random.choice(candidates)

def generate_literary(refresh_date):
    cached = load_daily("literary", refresh_date)
    if cached:
        return cached

    used = load_content_history("literary")
    literary_type = _pick_literary_type()
    prompt = f"""아래 조건에 맞게 한국어 글을 작성해주세요.

[유형]
{LITERARY_TYPE_GUIDE[literary_type]}

[필수 조건]
- 한국어로만 작성
- 500자 이상
- 첫 줄에 반드시 "주제: (책 제목 또는 인물 이름 또는 사자성어)" 형식으로 시작
- 이미 사용된 주제는 반드시 제외: {', '.join(used) if used else '없음'}"""

    content = call_claude(prompt)
    save_daily("literary", refresh_date, content)
    save_content_history("literary_type", literary_type)
    return content

with st.container(key="quote_section"):
    st.header("슬쩍 읽어보기")

    try:
        literary = generate_literary(refresh_date)
        lines = literary.strip().split("\n", 1)
        topic = lines[0].replace("주제:", "").strip()
        body = lines[1].strip() if len(lines) > 1 else literary

        st.caption(f"오늘의 주제: {topic}")
        st.markdown(body)

        if "literary_saved" not in st.session_state:
            save_content_history("literary", topic)
            st.session_state.literary_saved = True

    except Exception as e:
        st.error(f"글귀 생성 오류: {e}")

st.divider()

# ══════════════════════════════════════════════════
# 오늘의 TMI
# ══════════════════════════════════════════════════
def generate_tmi(refresh_date):
    cached = load_daily("tmi", refresh_date)
    if cached:
        return cached

    used = load_content_history("tmi")
    prompt = f"""흥미롭고 잘 알려지지 않은 사실을 한국어로 작성해주세요.

[구성 — 3줄 이상]
1. 핵심 사실: 놀랍거나 신기한 팩트 한 문장
2. 배경 설명: 왜 그런지, 어떻게 그렇게 되는지
3. 연결 정보: 이 사실과 연결된 흥미로운 추가 정보

[조건]
- 한국어로만 작성
- 실제 사실에 근거할 것
- 가볍게 읽히면서 대화 소재가 될 수 있는 주제
- 이미 사용된 주제는 제외: {', '.join(used) if used else '없음'}
- 첫 줄에 "주제: (주제 키워드)" 형식으로 시작"""

    content = call_claude(prompt, max_tokens=800)
    save_daily("tmi", refresh_date, content)
    return content

with st.container(key="tmi_section"):
    st.header("슬쩍 TMI")

    try:
        tmi = generate_tmi(refresh_date)
        lines = tmi.strip().split("\n", 1)
        topic = lines[0].replace("주제:", "").strip()
        body = lines[1].strip() if len(lines) > 1 else tmi

        st.caption(f"오늘의 주제: {topic}")
        st.markdown(body)

        if "tmi_saved" not in st.session_state:
            save_content_history("tmi", topic)
            st.session_state.tmi_saved = True

    except Exception as e:
        st.error(f"TMI 생성 오류: {e}")

st.divider()

# ══════════════════════════════════════════════════
# 오늘의 논쟁
# ══════════════════════════════════════════════════
def generate_debate(refresh_date):
    cached = load_daily("debate", refresh_date)
    if cached:
        return cached

    used = load_content_history("debate")
    prompt = f"""오늘의 가벼운 논쟁 주제를 한국어로 만들어주세요.

[조건]
- 양자택일 형식 (A vs B)
- 질문은 구체적인 상황을 3문장 이상으로 묘사해서, 답변자가 그 상황에 이입해 진지하게 고민하게 만들 것 (단순 취향 질문 금지)
- 답변에서 그 사람의 성격·기호·성향이 자연스럽게 드러나는 주제
- 정치·종교·예민한 사회 이슈 배제
- 뻔하거나 이미 유명한 주제(탕수육 부먹·찍먹 등) 배제
- 한국어로만 작성
- 이미 사용된 주제는 제외: {', '.join(used) if used else '없음'}

[출력 형식]
주제: (주제 키워드)
질문: (상황을 담은 3문장 이상의 질문. 줄바꿈 없이 이어서 작성)
A: (선택지 A)
B: (선택지 B)"""

    content = call_claude(prompt, max_tokens=900)
    save_daily("debate", refresh_date, content)
    return content

with st.container(key="debate_section"):
    st.header("슬쩍 토론")

    try:
        debate = generate_debate(refresh_date)
        parsed = {}
        for line in debate.strip().splitlines():
            for key in ("주제", "질문", "A", "B"):
                if line.startswith(f"{key}:"):
                    parsed[key] = line[len(key)+1:].strip()
                    break

        st.caption(f"오늘의 주제: {parsed.get('주제', '')}")
        if "질문" in parsed:
            st.markdown(f"**{parsed['질문']}**")
        if "A" in parsed:
            st.markdown(f"**A.** {parsed['A']}")
        if "B" in parsed:
            st.markdown(f"**B.** {parsed['B']}")

        if "debate_saved" not in st.session_state:
            save_content_history("debate", parsed.get("주제", ""))
            st.session_state.debate_saved = True

    except Exception as e:
        st.error(f"논쟁 생성 오류: {e}")
