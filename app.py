"""
MT_Inventory - 설비 유지보수 부품 관리 시스템 (EqMS)
메인 애플리케이션 파일
"""
import streamlit as st
import os
import sys
from datetime import datetime

# 모듈 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 설정 및 유틸리티 가져오기
from config.config import PAGE_TITLE, PAGE_ICON, PAGES, DEFAULT_LANGUAGE
from utils.auth import authenticate_user, check_authentication, logout, get_user_role, check_login_credentials, update_last_login
from utils.i18n import get_text, language_selector
from utils.helpers import display_error, display_success, display_info

# 페이지 모듈 가져오기
from pages.admin_management import admin_management
from pages.user_management import user_management
from pages.supabase_settings import supabase_settings

# 세션 상태 초기화
if 'language' not in st.session_state:
    st.session_state.language = DEFAULT_LANGUAGE

# 페이지 설정
st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=PAGE_ICON,
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS 스타일 적용
st.markdown("""
<style>
    /* 사이드바의 기본 내비게이션 메뉴 숨기기 */
    section[data-testid="stSidebar"] div.stButton {
        display: block !important;
    }
    section[data-testid="stSidebar"] > div:first-child {
        width: 100%;
    }
    section[data-testid="stSidebar"] div.block-container {
        padding-top: 1rem;
    }
    /* Streamlit 기본 페이지 탭 메뉴 숨기기 */
    [data-testid="stSidebarNav"] {
        display: none !important;
    }
    /* 사이드바 내 헤더 섹션 스타일링 */
    .sidebar-header {
        padding: 0.5rem 0 1rem 0;
    }
    /* 새로운 로그인 카드 스타일 */
    .login-container {
        padding: 2rem;
        border: none;
        background-color: transparent;
        max-width: 600px;
        margin: 2rem auto;
    }
    .login-title {
        font-size: 1.6rem;
        font-weight: bold;
        color: #1E3A8A;
        margin-bottom: 2rem;
        text-align: left;
        white-space: nowrap;
    }
    .login-input {
        margin-bottom: 1rem;
    }
    .login-button {
        background-color: #1E3A8A;
        color: white;
        font-weight: 600;
        padding: 0.5rem 1rem;
        border-radius: 4px;
        width: 100%;
        margin-top: 1rem;
    }
    /* 입력 필드 스타일링 */
    .login-form input {
        width: 100%;
        padding: 10px;
        border: 1px solid #ddd;
        border-radius: 4px;
        margin-bottom: 15px;
    }
    /* 공통 스타일 */
    .sidebar-text {
        font-size: 1.1rem;
        font-weight: 600;
        padding: 0.5rem 0;
        margin-bottom: 1rem;
        border-bottom: 1px solid #e1e1e1;
    }
    .sidebar-menu-item {
        display: flex;
        align-items: center;
        padding: 0.6rem 0.8rem;
        border-radius: 0.3rem;
        margin-bottom: 0.5rem;
        transition: background-color 0.2s;
    }
    .sidebar-menu-item:hover {
        background-color: #e6e9ef;
    }
    .sidebar-menu-item.active {
        background-color: #e6e9ef;
    }
    .sidebar-menu-icon {
        margin-right: 0.8rem;
        font-size: 1.2rem;
    }
    .language-selector {
        margin-bottom: 1.5rem;
    }
    /* 대시보드 카드 스타일 */
    .dashboard-card {
        background-color: #f8f9fc;
        border-radius: 8px;
        padding: 1.5rem;
        box-shadow: 0 0.15rem 1.75rem 0 rgba(58, 59, 69, 0.1);
        margin-bottom: 1.5rem;
    }
    .dashboard-card h3 {
        margin-top: 0;
        color: #1E3A8A;
        font-size: 1.2rem;
        margin-bottom: 1rem;
    }
    /* 폼 스타일링 */
    form[data-testid="stForm"] {
        background-color: white !important;
        padding: 0 !important;
        border-radius: 0 !important;
        box-shadow: none !important;
    }
    /* 폼 내부 버튼 */
    form[data-testid="stForm"] button[kind="formSubmit"] {
        background-color: #1E3A8A !important;
        color: white !important;
        font-weight: 600 !important;
        min-height: 40px !important;
        font-size: 1rem !important;
        border-radius: 4px !important;
    }
    /* 페이지 타이틀 스타일 개선 */
    .page-title {
        font-size: 1.8rem !important;
        font-weight: bold !important;
        color: #1E3A8A !important;
        margin-bottom: 1.5rem !important;
        padding-bottom: 0.5rem !important;
        border-bottom: 2px solid #e0e0e0 !important;
    }
    
    /* main-header 클래스 스타일 - 페이지 모듈에서 사용 */
    .main-header {
        font-size: 1.8rem !important;
        font-weight: bold !important;
        color: #1E3A8A !important;
        margin-bottom: 1.5rem !important;
        padding-bottom: 0.5rem !important;
        border-bottom: 2px solid #e0e0e0 !important;
    }
</style>
""", unsafe_allow_html=True)

def main():
    """
    메인 함수
    """
    # 사이드바
    with st.sidebar:
        # 언어 선택 상단에 배치
        st.markdown("<div class='language-selector'>", unsafe_allow_html=True)
        language_selector()
        st.markdown("</div>", unsafe_allow_html=True)
        
        # 로고와 앱 이름 (이미지 사용)
        col1, col2, col3 = st.columns([1, 3, 1])
        with col2:
            st.image("assets/images/worker1.png", width=120)
        
        # 앱 이름
        st.markdown("<div style='text-align: center; margin-top: 0.5rem;'><div style='font-weight: bold; color: #1E3A8A; font-size: 1.2rem;'>ALMUS EqMS SYSTEM</div></div>", unsafe_allow_html=True)
        st.markdown("<div class='sidebar-text'>설비 유지보수 부품 관리 시스템</div>", unsafe_allow_html=True)
        
        st.divider()
        
        # 인증 성공 시 메뉴 표시
        if check_authentication():
            # 사용자 역할 가져오기
            user_role = get_user_role()
            
            # 메뉴 옵션 및 아이콘
            admin_icons = ["👥", "🔐", "🔧", "📊", "📦", "📥", "📤", "🏢", "📝"]
            admin_pages = {
                "admin_management": "관리자 관리",
                "user_management": "사용자 관리", 
                "supabase_settings": "Supabase 설정",
                **PAGES
            }
            
            user_icons = ["📊", "📦", "📥", "📤", "🏢", "📝"]
            user_pages = PAGES.copy()
            
            # 역할에 따른 메뉴 표시
            if user_role == 'system_admin':
                display_pages = admin_pages
                icons = admin_icons
            elif user_role == 'admin':
                # 관리자는 관리자 관리 및 Supabase 설정 제외
                display_pages = {k: v for k, v in admin_pages.items() if k != 'admin_management' and k != 'supabase_settings'}
                icons = admin_icons[1:] # 관리자 관리 아이콘 제외
            else:
                # 일반 사용자는 기본 페이지만
                display_pages = user_pages
                icons = user_icons
            
            # 인덱스 오류 방지를 위해 아이콘 리스트 길이 확인 및 조정
            if len(icons) < len(display_pages):
                # 부족한 아이콘 수만큼 기본 아이콘(📋) 추가
                icons.extend(['📋'] * (len(display_pages) - len(icons)))
            
            for i, (key, label) in enumerate(display_pages.items()):
                menu_class = "sidebar-menu-item"
                if "selected_menu" in st.session_state and st.session_state.selected_menu == key:
                    menu_class += " active"
                
                # 인덱스 범위 확인
                icon_idx = min(i, len(icons) - 1)
                
                if st.sidebar.button(
                    f"{icons[icon_idx]} {get_text(key) if key in PAGES else label}", 
                    key=f"menu_{key}",
                    help=get_text(key) if key in PAGES else label,
                    use_container_width=True
                ):
                    st.session_state.selected_menu = key
            
            # 로그아웃 버튼
            st.sidebar.button(
                f"🚪 {get_text('logout')}", 
                key="logout", 
                on_click=logout,
                use_container_width=True
            )
    
    # 메인 화면
    if not check_authentication():
        # 첫 번째 이미지 스타일처럼 로그인 화면 구성
        st.markdown("""
        <div class='login-container'>
            <h1 class='login-title'>설비 유지보수 부품 관리 시스템 (EqMS)</h1>
        """, unsafe_allow_html=True)
        
        # 로그인 폼 - 간단한 디자인으로
        with st.form(key="login_form", clear_on_submit=False):
            username = st.text_input("이메일", key="username_input", placeholder="사용자 아이디를 입력하세요", value="")
            password = st.text_input("비밀번호", type="password", key="password_input", placeholder="비밀번호를 입력하세요", value="")
            
            # 디버깅 정보 표시 체크박스 (선택적)
            debug_info = st.checkbox("디버그 정보 표시", value=True, key="debug_checkbox")
            
            submit_button = st.form_submit_button("로그인", use_container_width=True)
            
            if submit_button:
                if debug_info:
                    st.write(f"로그인 시도: 사용자={username}, 비밀번호 길이={len(password if password else '')}")
                
                # 사용자 인증 및 데이터 가져오기
                user_data = check_login_credentials(username, password)
                if user_data:
                    # 로그인 성공, 세션 상태 업데이트
                    st.session_state['authenticated'] = True
                    st.session_state['username'] = username
                    st.session_state['user_data'] = user_data
                    
                    # 로그인 시간 업데이트
                    update_last_login(user_data['user_id'])
                    
                    # 페이지 리로드
                    st.rerun()
                else:
                    if debug_info:
                        from utils.auth import load_auth_config
                        config = load_auth_config()
                        if config:
                            st.write(f"사용 가능한 계정: {list(config['credentials']['usernames'].keys())}")
                    st.error(f"아이디 또는 비밀번호가 올바르지 않습니다. (입력한 이메일: {username})")
        
        # HTML 닫기
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        # 선택된 메뉴가 없으면 대시보드 기본 설정
        if "selected_menu" not in st.session_state:
            st.session_state.selected_menu = "dashboard"
        
        # 메뉴에 따라 페이지 로드
        selected_menu = st.session_state.selected_menu
        
        try:
            if selected_menu == "dashboard":
                display_dashboard()
            elif selected_menu == "parts":
                from pages.parts import show
                show()
            elif selected_menu == "inventory":
                from pages.inventory import show
                show()
            elif selected_menu == "inbound":
                from pages.inbound import show
                show()
            elif selected_menu == "outbound":
                from pages.outbound import show
                show()
            elif selected_menu == "suppliers":
                from pages.suppliers import show
                show()
            elif selected_menu == "reports":
                from pages.reports import show
                show()
            elif selected_menu == "admin_management":
                admin_management()
            elif selected_menu == "user_management":
                user_management()
            elif selected_menu == "supabase_settings":
                supabase_settings()
        except ImportError as e:
            st.error(f"페이지 로드 중 오류가 발생했습니다: {e}")
            st.info("개발 중인 페이지입니다. 곧 서비스될 예정입니다.")
            if st.checkbox("디버그 정보 표시"):
                st.exception(e)

def display_dashboard():
    """
    대시보드 표시
    """
    # 대시보드 페이지 타이틀 추가
    st.markdown(f"<div class='main-header'>{get_text('dashboard')}</div>", unsafe_allow_html=True)
    
    # 현재 날짜 표시
    current_date = datetime.now().strftime("%Y년 %m월 %d일")
    st.markdown(f"<div style='text-align:right; margin-bottom:1rem;'>{current_date}</div>", unsafe_allow_html=True)
    
    # 대시보드 컨텐츠
    col1, col2, col3 = st.columns(3)
    
    # 재고 요약
    with col1:
        st.markdown("""
        <div class='dashboard-card'>
            <h3>재고 요약</h3>
            <p>데이터베이스 연결이 필요합니다.</p>
        </div>
        """, unsafe_allow_html=True)
    
    # 최근 입고 현황
    with col2:
        st.markdown("""
        <div class='dashboard-card'>
            <h3>최근 입고 현황</h3>
            <p>데이터베이스 연결이 필요합니다.</p>
        </div>
        """, unsafe_allow_html=True)
    
    # 최근 출고 현황
    with col3:
        st.markdown("""
        <div class='dashboard-card'>
            <h3>최근 출고 현황</h3>
            <p>데이터베이스 연결이 필요합니다.</p>
        </div>
        """, unsafe_allow_html=True)
    
    # 재고 부족 아이템 목록
    st.markdown("""
    <div class='dashboard-card'>
        <h3>재고 부족 아이템</h3>
        <p>데이터베이스 연결이 필요합니다.</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main() 