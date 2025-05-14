"""
재고 관리 모듈
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import sys
import os
from datetime import datetime
import logging

# 모듈 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.helpers import display_error, display_success, display_info, display_warning, format_date, format_currency
from utils.i18n import get_text
from database.supabase_client import supabase

logger = logging.getLogger(__name__)

# 카테고리 목록 조회 함수 - 캐싱 적용
@st.cache_data(ttl=3600)  # 1시간 동안 캐싱
def get_categories():
    """카테고리 목록을 가져옵니다."""
    try:
        category_result = supabase().from_("parts").select("category").execute()
        categories = []
        if category_result.data:
            for item in category_result.data:
                if item.get('category') and item.get('category') not in categories:
                    categories.append(item.get('category'))
            # 중복 제거 및 정렬
            categories = sorted(list(set(categories)))
        
        # "전체" 옵션을 맨 앞에 추가
        return ["전체"] + categories
    except Exception as e:
        logger.error(f"카테고리 정보 조회 중 오류: {e}")
        # 오류 발생 시 기본 옵션 사용
        return ["전체"]

# 부품 데이터를 가져오는 함수 - 캐싱 적용
@st.cache_data(ttl=300)  # 5분 동안 캐싱
def get_parts(search_code=None, search_name=None, search_category=None, name_display="영문명"):
    """검색 조건에 맞는 부품 데이터를 가져옵니다."""
    try:
        # 필요한 필드만 선택
        query = supabase().from_("parts").select("part_id, part_code, part_name, korean_name, vietnamese_name, category, unit, min_stock")
        
        # 검색 필터 적용
        if search_code:
            query = query.ilike("part_code", f"%{search_code}%")
        
        if search_name:
            if name_display == "영문명":
                query = query.ilike("part_name", f"%{search_name}%")
            elif name_display == "한국어명":
                query = query.ilike("korean_name", f"%{search_name}%")
            else:  # 베트남어명
                query = query.ilike("vietnamese_name", f"%{search_name}%")
        
        if search_category and search_category != "전체":
            query = query.eq("category", search_category)
        
        # 쿼리 실행
        result = query.execute()
        
        return result.data
    except Exception as e:
        logger.error(f"부품 데이터 조회 중 오류: {e}")
        return []

# 재고 정보를 가져오는 함수 - 캐싱 적용
@st.cache_data(ttl=300)  # 5분 동안 캐싱
def get_inventory_data(part_ids):
    """부품 ID 목록에 대한 재고 정보를 가져옵니다."""
    inventory_data = {}
    
    if not part_ids:
        return inventory_data
    
    # 배치 처리
    batch_size = 30  # 한 번에 처리할 ID 수
    for i in range(0, len(part_ids), batch_size):
        batch_ids = part_ids[i:i+batch_size]
        try:
            inventory_result = supabase().from_("inventory").select("part_id, current_quantity").in_("part_id", batch_ids).execute()
            for item in inventory_result.data:
                inventory_data[item['part_id']] = item.get('current_quantity', 0) or 0  # None 값 안전 처리
        except Exception as e:
            logger.error(f"재고 정보 조회 중 오류: {e}")
    
    return inventory_data

# 가격 정보를 가져오는 함수 - 캐싱 적용
@st.cache_data(ttl=300)  # 5분 동안 캐싱
def get_price_data(part_ids):
    """부품 ID 목록에 대한 가격 정보를 가져옵니다."""
    price_data = {}
    
    if not part_ids:
        return price_data
    
    # 배치 처리
    batch_size = 30  # 한 번에 처리할 ID 수
    for i in range(0, len(part_ids), batch_size):
        batch_ids = part_ids[i:i+batch_size]
        try:
            price_result = supabase().from_("part_prices").select("part_id, unit_price").in_("part_id", batch_ids).eq("is_current", True).execute()
            for item in price_result.data:
                price_data[item['part_id']] = item.get('unit_price', 0) or 0  # None 값 안전 처리
        except Exception as e:
            logger.error(f"가격 정보 조회 중 오류: {e}")
    
    return price_data

# 재고 부족 부품 목록 조회 함수 - 캐싱 적용
@st.cache_data(ttl=300)  # 5분 동안 캐싱
def get_low_stock_items():
    """재고 부족 부품 목록을 가져옵니다."""
    try:
        # 필요한 필드만 선택하여 부품 데이터 조회
        parts_data = supabase().from_("parts").select("part_id, part_code, part_name, korean_name, category, unit, min_stock").execute()
        
        if not parts_data.data:
            return []
        
        # 재고 부족 아이템 찾기
        low_stock_items = []
        part_ids = [part['part_id'] for part in parts_data.data]
        
        # 효율적인 재고 조회를 위한 배치 처리
        inventory_map = {}
        batch_size = 30
        
        for i in range(0, len(part_ids), batch_size):
            batch_ids = part_ids[i:i+batch_size]
            try:
                inventory_result = supabase().from_("inventory").select("part_id, current_quantity").in_("part_id", batch_ids).execute()
                for item in inventory_result.data:
                    inventory_map[item['part_id']] = item.get('current_quantity', 0) or 0
            except Exception as e:
                logger.error(f"재고 정보 조회 중 오류: {e}")
        
        # 재고 부족 판단
        for part in parts_data.data:
            part_id = part['part_id']
            # None 값 안전 처리
            min_stock = part['min_stock'] if part['min_stock'] is not None else 0
            current_quantity = inventory_map.get(part_id, 0)
            
            # 재고가 최소 재고량보다 적은 경우
            if current_quantity < min_stock:
                # 부족량 계산
                shortage = min_stock - current_quantity
                
                low_stock_items.append({
                    'part_id': part_id,
                    'part_code': part['part_code'],
                    'part_name': part['part_name'],
                    'korean_name': part.get('korean_name', ''),
                    'category': part.get('category', ''),
                    'unit': part.get('unit', ''),
                    'current_quantity': current_quantity,
                    'min_stock': min_stock,
                    'shortage': shortage
                })
        
        # 부족량 기준으로 정렬
        return sorted(low_stock_items, key=lambda x: x['shortage'], reverse=True)
    
    except Exception as e:
        logger.error(f"재고 부족 아이템 조회 중 오류: {e}")
        return []

# 최근 입출고 정보 조회 함수 - 캐싱 적용
@st.cache_data(ttl=300)  # 5분 동안 캐싱
def get_recent_inventory_activity(part_id):
    """부품의 최근 입출고 정보를 가져옵니다."""
    try:
        # 최근 입고일 조회
        inbound_result = supabase().from_("inbound").select("inbound_date").eq("part_id", part_id).order("inbound_date", desc=True).limit(1).execute()
        last_inbound_date = inbound_result.data[0]['inbound_date'] if inbound_result.data else None
        
        # 최근 출고일 조회
        outbound_result = supabase().from_("outbound").select("outbound_date").eq("part_id", part_id).order("outbound_date", desc=True).limit(1).execute()
        last_outbound_date = outbound_result.data[0]['outbound_date'] if outbound_result.data else None
        
        return last_inbound_date, last_outbound_date
    except Exception as e:
        logger.error(f"최근 입출고 정보 조회 중 오류: {e}")
        return None, None

# 재고 분석 데이터 조회 함수 - 캐싱 적용
@st.cache_data(ttl=300)  # 5분 동안 캐싱
def get_inventory_analysis_data():
    """재고 분석을 위한 데이터를 조회합니다."""
    try:
        # 카테고리별 부품 수와 총 가치 계산 - 효율성 개선
        # 1. 먼저 모든 부품 카테고리 정보를 한 번에 가져옴
        parts_result = supabase().from_("parts").select("part_id, category").execute()
        
        # 카테고리별 데이터 집계 및 부품 ID 목록 준비
        categories = {}
        part_ids_by_category = {}
        all_part_ids = []
        
        for item in parts_result.data:
            part_id = item.get('part_id')
            cat = item.get('category', '기타')
            if not cat:  # 카테고리가 None이거나 빈 문자열인 경우
                cat = '기타'
            
            # 카테고리별 부품 수 집계
            if cat in categories:
                categories[cat] += 1
            else:
                categories[cat] = 1
                part_ids_by_category[cat] = []
            
            # 카테고리별 부품 ID 목록 생성
            part_ids_by_category[cat].append(part_id)
            all_part_ids.append(part_id)
        
        # 2. 모든 부품의 재고 정보를 가져옴 - 배치 처리 사용
        inventory_data = get_inventory_data(all_part_ids)
        
        # 3. 모든 부품의 가격 정보를 가져옴 - 배치 처리 사용
        price_data = get_price_data(all_part_ids)
        
        # 카테고리별 가치 계산
        category_values = {}
        for cat, part_ids in part_ids_by_category.items():
            total_value = 0
            for part_id in part_ids:
                quantity = inventory_data.get(part_id, 0)
                price = price_data.get(part_id, 0)
                total_value += quantity * price
            
            category_values[cat] = total_value
            
        # 데이터프레임 생성
        category_data = []
        for cat, count in categories.items():
            category_data.append({
                'category': cat,
                'count': count,
                'total_value': category_values.get(cat, 0)
            })
            
        category_df = pd.DataFrame(category_data)
        
        # 상태별 부품 수 집계도 개선
        status_result = supabase().from_("parts").select("status").execute()
        
        # 실제 상태값 집계
        status_counts = {}
        
        for item in status_result.data:
            status = item.get('status', '')
            if status:
                if status in status_counts:
                    status_counts[status] += 1
                else:
                    status_counts[status] = 1
        
        # 기본 상태값이 없는 경우 초기화
        for status in ['NEW', 'OLD', 'REPAIR', 'NG']:
            if status not in status_counts:
                status_counts[status] = 0
                
        status_data = []
        for status, count in status_counts.items():
            status_data.append({
                'status': status,
                'count': count
            })
            
        status_df = pd.DataFrame(status_data)
        
        # 재고 요약 데이터 - 효율성 개선
        # 총 부품 수는 이미 계산 완료
        total_parts = len(all_part_ids)
        
        # 총 재고량 - 이미 inventory_data에 있는 정보 활용
        total_quantity = sum(inventory_data.values())
        
        # 총 재고 가치 - 이미 category_values에 있는 정보 활용
        total_value = sum(category_values.values())
        
        # 재고 부족 부품 수 계산 - 효율성 개선
        # 부품별 최소 재고량 정보 가져오기
        min_stock_result = supabase().from_("parts").select("part_id, min_stock").execute()
        min_stock_data = {}
        for item in min_stock_result.data:
            # None 값 안전 처리
            min_stock_data[item['part_id']] = 0 if item.get('min_stock') is None else item.get('min_stock', 0)
        
        # 재고 부족 계산
        low_stock_count = 0
        for part_id, min_stock in min_stock_data.items():
            current_qty = inventory_data.get(part_id, 0)
            if current_qty < min_stock:
                low_stock_count += 1
        
        summary_data = {
            'total_parts': total_parts,
            'total_quantity': total_quantity,
            'total_value': total_value,
            'low_stock_parts': low_stock_count
        }
        
        # 재고 회전율 데이터 (샘플 데이터로 대체)
        months = ['2023-05', '2023-06', '2023-07', '2023-08', '2023-09', '2023-10', 
                '2023-11', '2023-12', '2024-01', '2024-02', '2024-03', '2024-04']
        turnover_rate = [2.1, 2.2, 2.0, 2.3, 2.4, 2.5, 2.3, 2.2, 2.1, 2.0, 2.2, 2.3]
        
        turnover_df = pd.DataFrame({
            'month': months,
            'turnover_rate': turnover_rate
        })
        
        return {
            'category_df': category_df,
            'status_df': status_df,
            'summary_data': summary_data,
            'turnover_df': turnover_df
        }
        
    except Exception as e:
        logger.error(f"재고 분석 데이터 조회 중 오류: {e}")
        return None

def show():
    """
    재고 관리 페이지 표시
    """
    st.markdown(f"<div class='main-header'>{get_text('inventory')}</div>", unsafe_allow_html=True)
    
    # 탭 설정
    tabs = st.tabs([
        f"📋 {get_text('current_stock')}",
        f"⚠️ 재고 부족 알림",
        f"📊 재고 분석"
    ])
    
    # 현재 재고 탭
    with tabs[0]:
        show_current_inventory()
    
    # 재고 부족 탭
    with tabs[1]:
        show_low_stock_alerts()
    
    # 재고 분석 탭
    with tabs[2]:
        show_inventory_analysis()

def show_current_inventory():
    """
    현재 재고 현황 표시
    """
    # 필터 옵션
    col1, col2, col3 = st.columns(3)
    
    with col1:
        search_code = st.text_input(f"{get_text('part_code')} {get_text('search')}", placeholder="MT001")
    with col2:
        search_name = st.text_input(f"{get_text('part_name')} {get_text('search')}", placeholder="FILTER")
    with col3:
        # 캐싱된 함수를 사용하여 카테고리 가져오기
        category_options = get_categories()
        search_category = st.selectbox(f"{get_text('category')} {get_text('filter')}", category_options)
    
    # 이름 표시 옵션
    name_display_options = ["영문명", "한국어명", "베트남어명"]
    name_display = st.radio("이름 표시 옵션", name_display_options, horizontal=True)
    
    # 검색 버튼
    if st.button(f"🔍 {get_text('search')}", type="primary"):
        # 로딩 상태 표시
        with st.spinner("데이터를 불러오는 중..."):
            # 캐싱된 함수를 사용하여 부품 데이터 가져오기
            parts_data = get_parts(search_code, search_name, search_category, name_display)
            
            if not parts_data:
                display_info("검색 결과가 없습니다.")
                return
            
            # 부품 ID 목록
            part_ids = [item['part_id'] for item in parts_data]
            
            # 캐싱된 함수를 사용하여 재고 및 가격 정보 가져오기
            inventory_data = get_inventory_data(part_ids)
            price_data = get_price_data(part_ids)
            
            # 결과 데이터 조합
            combined_data = []
            for part in parts_data:
                part_id = part['part_id']
                inventory_info = inventory_data.get(part_id, 0)
                unit_price = price_data.get(part_id, 0)
                
                # None 값 안전 처리
                min_stock = part.get('min_stock', 0) if part.get('min_stock') is not None else 0
                
                # 총 가치 계산
                total_value = inventory_info * unit_price
                
                # 상태 결정
                status = '부족' if inventory_info < min_stock else '정상'
                
                # 결과 데이터에 추가
                combined_data.append({
                    'part_id': part_id,
                    'part_code': part['part_code'],
                    'part_name': part['part_name'],
                    'korean_name': part.get('korean_name', ''),
                    'vietnamese_name': part.get('vietnamese_name', ''),
                    'category': part.get('category', ''),
                    'unit': part.get('unit', ''),
                    'current_quantity': inventory_info,
                    'min_stock': min_stock,
                    'unit_price': unit_price,
                    'total_value': total_value,
                    'status': status
                })
            
            # 데이터프레임으로 변환
            df = pd.DataFrame(combined_data)
            
            # 이름 표시 설정에 따라 표시할 이름 컬럼 선택
            display_name_column = 'part_name'
            if name_display == "한국어명":
                display_name_column = 'korean_name'
            elif name_display == "베트남어명":
                display_name_column = 'vietnamese_name'
            
            # 결과 표시용 컬럼 재구성
            display_df = df[[
                'part_code', 
                display_name_column, 
                'category', 
                'unit', 
                'current_quantity', 
                'min_stock', 
                'total_value', 
                'status'
            ]].copy()
            
            # 컬럼명 변경
            display_df.columns = [
                get_text('part_code'),
                get_text('part_name'),
                get_text('category'),
                get_text('unit'),
                get_text('current_stock'),
                get_text('min_stock'),
                get_text('total'),
                get_text('status')
            ]
            
            st.dataframe(
                display_df,
                column_config={
                    get_text('part_code'): st.column_config.TextColumn(get_text('part_code')),
                    get_text('part_name'): st.column_config.TextColumn(get_text('part_name')),
                    get_text('category'): st.column_config.TextColumn(get_text('category')),
                    get_text('unit'): st.column_config.TextColumn(get_text('unit')),
                    get_text('current_stock'): st.column_config.NumberColumn(get_text('current_stock'), format="%d"),
                    get_text('min_stock'): st.column_config.NumberColumn(get_text('min_stock'), format="%d"),
                    get_text('total'): st.column_config.NumberColumn(get_text('total'), format="₫%d"),
                    get_text('status'): st.column_config.TextColumn(get_text('status'))
                },
                use_container_width=True,
                hide_index=True
            )
            
            # 재고 총액 계산
            total_inventory_value = df['total_value'].sum()
            st.markdown(f"### 재고 총액: {format_currency(total_inventory_value)}")
            
            # 내보내기 버튼
            if st.button(f"📥 Excel {get_text('save')}"):
                # Excel 저장 로직
                current_date = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"inventory_export_{current_date}.xlsx"
                
                # 데이터프레임을 엑셀로 변환
                df.to_excel(filename, index=False)
                
                # 다운로드 링크 생성
                with open(filename, "rb") as file:
                    st.download_button(
                        label=f"📥 {filename} 다운로드",
                        data=file,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                
                display_success(f"Excel 파일로 저장되었습니다: {filename}")
        except Exception as e:
            display_error(f"데이터 검색 중 오류가 발생했습니다: {e}")

def show_low_stock_alerts():
    """
    재고 부족 알림 표시
    """
    st.markdown("### 재고 부족 부품 목록")
    st.info("최소 재고량보다 현재 재고량이 적은 부품 목록입니다.")
    
    # 로딩 상태 표시
    with st.spinner("재고 부족 부품을 분석 중..."):
        # 캐싱된 함수를 사용하여 재고 부족 아이템 가져오기
        low_stock_items = get_low_stock_items()
        
        # 결과가 없으면 메시지 표시
        if not low_stock_items:
            st.success("모든 부품이 최소 재고량을 충족하고 있습니다.")
            return
        
        # 최근 입출고 정보 추가
        for item in low_stock_items:
            last_inbound_date, last_outbound_date = get_recent_inventory_activity(item['part_id'])
            item['last_inbound_date'] = last_inbound_date
            item['last_outbound_date'] = last_outbound_date
        
        # 데이터프레임으로 변환
        df = pd.DataFrame(low_stock_items)
            
        # 알림 표시
        st.dataframe(
            df,
            column_config={
                'part_code': st.column_config.TextColumn(get_text('part_code')),
                'part_name': st.column_config.TextColumn(get_text('part_name')),
                'korean_name': st.column_config.TextColumn(get_text('korean_name')),
                'category': st.column_config.TextColumn(get_text('category')),
                'unit': st.column_config.TextColumn(get_text('unit')),
                'current_quantity': st.column_config.NumberColumn(get_text('current_stock'), format="%d"),
                'min_stock': st.column_config.NumberColumn(get_text('min_stock'), format="%d"),
                'shortage': st.column_config.NumberColumn("부족 수량", format="%d"),
                'last_inbound_date': st.column_config.DateColumn("최근 입고일", format="YYYY-MM-DD"),
                'last_outbound_date': st.column_config.DateColumn("최근 출고일", format="YYYY-MM-DD")
            },
            use_container_width=True,
            hide_index=True
        )
        
        # 발주 요청 버튼
        if st.button("📝 발주 요청서 생성"):
            # 발주 요청서 생성 로직
            current_date = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"purchase_request_{current_date}.xlsx"
            
            # 요청서 데이터 준비
            purchase_df = df[['part_code', 'part_name', 'korean_name', 'category', 'unit', 'current_quantity', 'min_stock', 'shortage']].copy()
            purchase_df['요청수량'] = purchase_df['shortage']
            
            # 데이터프레임을 엑셀로 변환
            purchase_df.to_excel(filename, index=False)
            
            # 다운로드 링크 생성
            with open(filename, "rb") as file:
                st.download_button(
                    label=f"📥 {filename} 다운로드",
                    data=file,
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            
            display_success(f"발주 요청서가 생성되었습니다: {filename}")
    except Exception as e:
        display_error(f"데이터 검색 중 오류가 발생했습니다: {e}")

def show_inventory_analysis():
    """
    재고 분석 표시
    """
    st.markdown("### 재고 분석")
    
    # 로딩 상태 표시
    with st.spinner("재고 분석 데이터를 로딩 중..."):
        # 캐싱된 함수를 사용하여 분석 데이터 가져오기
        analysis_data = get_inventory_analysis_data()
        
        if not analysis_data:
            st.error("재고 분석 데이터를 가져오는 중 오류가 발생했습니다.")
            return
        
        category_df = analysis_data['category_df']
        status_df = analysis_data['status_df']
        summary_data = analysis_data['summary_data']
        turnover_df = analysis_data['turnover_df']
        
        # 데이터가 없는 경우 처리
        if category_df.empty:
            st.warning("카테고리별 데이터를 가져올 수 없습니다.")
            return
        
        if status_df.empty:
            st.warning("상태별 데이터를 가져올 수 없습니다.")
            return
        
        # 차트 표시
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 카테고리별 부품 수")
            fig1 = px.pie(
                category_df,
                values='count',
                names='category',
                title='카테고리별 부품 수'
            )
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            st.markdown("#### 상태별 부품 수")
            fig2 = px.pie(
                status_df,
                values='count',
                names='status',
                title='상태별 부품 수',
                color_discrete_sequence=px.colors.sequential.Blues
            )
            st.plotly_chart(fig2, use_container_width=True)
        
        # 카테고리별 재고 가치
        st.markdown("#### 카테고리별 재고 가치")
        fig3 = px.bar(
            category_df,
            x='category',
            y='total_value',
            title='카테고리별 재고 가치',
            labels={'category': '카테고리', 'total_value': '재고 가치'},
            color='category'
        )
        st.plotly_chart(fig3, use_container_width=True)
        
        # 재고 현황 요약
        st.markdown("#### 재고 현황 요약")
        
        # 요약 데이터 준비
        formatted_summary = {
            '항목': ['총 부품 종류', '총 재고량', '총 재고 가치', '재고 부족 부품 수'],
            '값': [
                f"{summary_data.get('total_parts', 0)}개",
                f"{summary_data.get('total_quantity', 0):,}개",
                f"{format_currency(summary_data.get('total_value', 0))}",
                f"{summary_data.get('low_stock_parts', 0)}개"
            ]
        }
        summary_df = pd.DataFrame(formatted_summary)
        
        # 요약 표 표시
        st.table(summary_df)
        
        # 추가 분석 옵션
        st.markdown("#### 추가 분석")
        analysis_options = st.multiselect(
            "분석 옵션 선택",
            ["재고 회전율", "밸류에이션 분석", "사용 패턴 분석", "예측 분석"],
            default=["재고 회전율"]
        )
        
        if "재고 회전율" in analysis_options:
            st.markdown("#### 재고 회전율 분석")
            st.info("최근 12개월 동안의 재고 회전율 추세를 보여줍니다.")
            
            fig4 = px.line(
                turnover_df,
                x='month',
                y='turnover_rate',
                title='월별 재고 회전율',
                markers=True
            )
            st.plotly_chart(fig4, use_container_width=True)
        
        # 발주 요청 버튼
        if st.button("📝 발주 요청서 생성"):
            # 캐싱된 함수를 사용하여 재고 부족 아이템 가져오기
            low_stock_items = get_low_stock_items()
            
            if not low_stock_items:
                st.info("재고 부족 부품이 없습니다.")
                return
                
            # 발주 요청서 생성 로직
            current_date = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"purchase_request_{current_date}.xlsx"
            
            # 데이터프레임 변환
            df_request = pd.DataFrame(low_stock_items)
            
            # 요청서 데이터 준비
            purchase_df = df_request[['part_code', 'part_name', 'korean_name', 'category', 'unit', 'current_quantity', 'min_stock', 'shortage']].copy()
            purchase_df['요청수량'] = purchase_df['shortage']
            
            # 데이터프레임을 엑셀로 변환
            purchase_df.to_excel(filename, index=False)
            
            # 다운로드 링크 생성
            with open(filename, "rb") as file:
                st.download_button(
                    label=f"📥 {filename} 다운로드",
                    data=file,
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            
            display_success(f"발주 요청서가 생성되었습니다: {filename}")

if __name__ == "__main__":
    show() 