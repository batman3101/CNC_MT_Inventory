"""
부품 관리 모듈
"""
import streamlit as st
import pandas as pd
import sys
import os
from datetime import datetime
import time

# 모듈 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.helpers import display_error, display_success, display_info, display_warning, format_date, format_currency
from utils.i18n import get_text
from database.supabase_client import supabase
from database.update_part import update_part, update_inventory  # 새로 만든 모듈 import

def show():
    """
    부품 관리 페이지 표시
    """
    st.markdown(f"<div class='main-header'>{get_text('parts')}</div>", unsafe_allow_html=True)
    
    # 탭 설정
    tabs = st.tabs([
        f"🔍 {get_text('search')}",
        f"➕ {get_text('add')}",
        f"📊 {get_text('details')}"
    ])
    
    # 검색 탭
    with tabs[0]:
        show_parts_search()
    
    # 추가 탭
    with tabs[1]:
        show_parts_add()
    
    # 상세 탭
    with tabs[2]:
        show_parts_details()

def show_parts_search():
    """
    부품 검색 화면 표시
    """
    # 검색 필터
    col1, col2, col3 = st.columns(3)
    
    with col1:
        search_code = st.text_input(f"{get_text('part_code')} {get_text('search')}", placeholder="MT001")
    with col2:
        search_name = st.text_input(f"{get_text('part_name')} {get_text('search')}", placeholder="COOLANT FILTER")
    with col3:
        # 상태 목록 가져오기
        try:
            status_result = supabase().from_("parts").select("status").execute()
            if status_result.data:
                # 중복 제거하고 고유 상태 추출
                statuses = list(set([item.get("status", "") for item in status_result.data if item.get("status")]))
                status_options = ["전체"] + sorted(statuses)
            else:
                # 기본 상태 옵션
                status_options = ["전체", "NEW", "OLD", "OLDER"]
        except Exception as e:
            st.warning(f"상태 정보를 불러오는 중 오류 발생: {e}")
            # 오류 발생 시 기본 옵션 사용
            status_options = ["전체", "NEW", "OLD", "OLDER"]
        
        search_status = st.selectbox(f"{get_text('status')} {get_text('filter')}", status_options)
    
    # 검색 버튼
    if st.button(f"🔍 {get_text('search')}", type="primary"):
        try:
            # Supabase에서 부품 데이터 조회
            query = supabase().from_("parts").select("*")
            
            # 검색 필터 적용
            if search_code:
                query = query.ilike("part_code", f"%{search_code}%")
            if search_name:
                query = query.ilike("part_name", f"%{search_name}%")
            if search_status != "전체":
                query = query.eq("status", search_status)
            
            # 결과 조회
            result = query.execute()
            
            # 데이터프레임으로 변환
            if result.data:
                df = pd.DataFrame(result.data)
                
                # 결과 표시
                st.dataframe(
                    df,
                    column_config={
                        'part_id': st.column_config.TextColumn(get_text('part_id')),
                        'part_code': st.column_config.TextColumn(get_text('part_code')),
                        'part_name': st.column_config.TextColumn(get_text('part_name')),
                        'spec': st.column_config.TextColumn(get_text('spec')),
                        'unit': st.column_config.TextColumn(get_text('unit')),
                        'status': st.column_config.TextColumn(get_text('status')),
                        'min_stock': st.column_config.NumberColumn(get_text('min_stock'), format="%d"),
                        'category': st.column_config.TextColumn(get_text('category')),
                        'created_at': st.column_config.DateColumn(get_text('created_at'), format="YYYY-MM-DD")
                    },
                    use_container_width=True,
                    hide_index=True
                )
                
                # 내보내기 버튼
                if st.button(f"📥 Excel {get_text('save')}"):
                    # Excel 저장 로직
                    current_date = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"parts_export_{current_date}.xlsx"
                    
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
            else:
                display_info("검색 결과가 없습니다.")
        except Exception as e:
            display_error(f"데이터 검색 중 오류가 발생했습니다: {e}")

def show_parts_add():
    """
    부품 추가 화면 표시
    """
    st.markdown(f"### 신규 부품 등록")
    
    # 입력 폼
    with st.form("add_part_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            part_code = st.text_input(f"{get_text('part_code')}*", placeholder="MT138")
            part_name = st.text_input(f"{get_text('part_name')}*", placeholder="COOLANT FILTER")
            vietnamese_name = st.text_input(f"{get_text('vietnamese_name')}", placeholder="LỌC CHẤT LÀMÁT")
            korean_name = st.text_input(f"{get_text('korean_name')}", placeholder="냉각수 필터")
            spec = st.text_input(f"{get_text('spec')}", placeholder="10in/200μm")
        
        with col2:
            unit_options = ["EA", "SET", "BOX", "KG", "L", "M", "PC"]
            unit = st.selectbox(f"{get_text('unit')}*", unit_options, index=0)
            
            category_options = ["필터", "펌프", "모터", "밸브", "센서", "기타"]
            category = st.selectbox(f"{get_text('category')}", category_options)
            
            # 상태 목록 가져오기
            try:
                status_result = supabase().from_("parts").select("status").execute()
                if status_result.data:
                    # 중복 제거하고 고유 상태 추출
                    statuses = list(set([item.get("status", "") for item in status_result.data if item.get("status")]))
                    # 필수 상태 값이 없으면 추가
                    required_statuses = ["NEW", "OLD", "OLDER"]
                    for req_status in required_statuses:
                        if req_status not in statuses:
                            statuses.append(req_status)
                    status_options = sorted(statuses)
                else:
                    # 기본 상태 옵션
                    status_options = ["NEW", "OLD", "OLDER"]
            except Exception as e:
                # 오류 발생 시 기본 옵션 사용
                status_options = ["NEW", "OLD", "OLDER"]
            
            status = st.selectbox(f"{get_text('status')}*", status_options, index=0)
            
            min_stock = st.number_input(f"{get_text('min_stock')}", min_value=0, value=5)
        
        description = st.text_area(f"{get_text('description')}", placeholder="부품에 대한 상세 설명")
        
        submitted = st.form_submit_button(f"✅ {get_text('save')}", use_container_width=True)
        
        if submitted:
            # 필수 입력 확인
            if not part_code:
                display_error("부품 코드는 필수 입력 항목입니다.")
            elif not part_name:
                display_error("부품명은 필수 입력 항목입니다.")
            else:
                try:
                    # 코드 중복 확인
                    duplicate_check = supabase().from_("parts").select("part_id").eq("part_code", part_code).execute()
                    if duplicate_check.data:
                        display_error(f"부품 코드 '{part_code}'는 이미 사용 중입니다. 다른 코드를 입력해주세요.")
                        return
                    
                    # 현재 사용자 정보 가져오기
                    from utils.auth import get_current_user
                    current_user = get_current_user()
                    
                    # Supabase에 저장할 데이터 준비
                    part_data = {
                        "part_code": part_code,
                        "part_name": part_name,
                        "vietnamese_name": vietnamese_name,
                        "korean_name": korean_name,
                        "spec": spec,
                        "unit": unit,
                        "category": category,
                        "status": status,
                        "min_stock": min_stock,
                        "description": description,
                        "created_by": current_user
                    }
                    
                    # Supabase에 저장
                    result = supabase().from_("parts").insert(part_data).execute()
                    
                    if result.data:
                        # 재고 테이블에도 초기 데이터 생성
                        part_id = result.data[0]["part_id"]
                        inventory_data = {
                            "part_id": part_id,
                            "current_quantity": 0
                        }
                        supabase().from_("inventory").insert(inventory_data).execute()
                        
                        display_success(f"새 부품 '{part_name}'이(가) 등록되었습니다. (코드: {part_code})")
                        # 폼 초기화
                        st.rerun()
                    else:
                        display_error("부품 등록 중 오류가 발생했습니다.")
                except Exception as e:
                    display_error(f"부품 등록 중 오류가 발생했습니다: {e}")

def show_parts_details():
    """
    부품 상세 정보 화면 표시
    """
    # 부품 목록 조회 (Supabase에서 가져옴)
    try:
        result = supabase().from_("parts").select("part_id, part_code, part_name").order("part_code").execute()
        if result.data:
            part_options = ["-- 부품 선택 --"] + [f"{item['part_code']} - {item['part_name']}" for item in result.data]
            part_ids = {f"{item['part_code']} - {item['part_name']}": item['part_id'] for item in result.data}
        else:
            part_options = ["-- 부품 선택 --"]
            part_ids = {}
    except Exception as e:
        st.error(f"부품 목록을 불러오는 중 오류가 발생했습니다: {e}")
        part_options = ["-- 부품 선택 --"]
        part_ids = {}
    
    selected_option = st.selectbox("부품 선택", part_options)
    
    if selected_option != "-- 부품 선택 --":
        # 선택한 부품 코드 추출
        selected_code = selected_option.split(" - ")[0]
        selected_id = part_ids.get(selected_option)
        
        # 선택한 부품 정보 조회
        try:
            # 부품 기본 정보 조회
            part_result = supabase().from_("parts").select("*").eq("part_id", selected_id).execute()
            
            if not part_result.data:
                display_error(f"선택한 부품 정보를 찾을 수 없습니다.")
                return
            
            part_data = part_result.data[0]
            
            # 재고 정보 조회
            inventory_result = supabase().from_("inventory").select("*").eq("part_id", selected_id).execute()
            current_stock = 0
            if inventory_result.data:
                current_stock = inventory_result.data[0]["current_quantity"]
            
            # 수정 모드 토글
            edit_mode = st.checkbox("수정 모드")
            
            if edit_mode:
                # 수정 폼
                with st.form("edit_part_form", clear_on_submit=False):
                    st.markdown("#### 부품 정보 수정")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        part_name = st.text_input("부품명*", value=part_data.get("part_name", ""))
                        vietnamese_name = st.text_input("베트남어명", value=part_data.get("vietnamese_name", ""))
                        korean_name = st.text_input("한국어명", value=part_data.get("korean_name", ""))
                        spec = st.text_input("사양", value=part_data.get("spec", ""))
                    
                    with col2:
                        unit_options = ["EA", "SET", "BOX", "KG", "L", "M", "PC"]
                        unit = st.selectbox("단위*", unit_options, index=unit_options.index(part_data.get("unit", "EA")))
                        
                        category_options = ["필터", "펌프", "모터", "밸브", "센서", "기타"]
                        category = st.selectbox("카테고리", category_options, 
                                              index=category_options.index(part_data.get("category", "필터")) if part_data.get("category") in category_options else 0)
                        
                        # 상태 목록 가져오기
                        try:
                            status_result = supabase().from_("parts").select("status").execute()
                            if status_result.data:
                                # 중복 제거하고 고유 상태 추출
                                statuses = list(set([item.get("status", "") for item in status_result.data if item.get("status")]))
                                # 필수 상태 값이 없으면 추가
                                required_statuses = ["NEW", "OLD", "OLDER"]
                                for req_status in required_statuses:
                                    if req_status not in statuses:
                                        statuses.append(req_status)
                                status_options = sorted(statuses)
                            else:
                                # 기본 상태 옵션
                                status_options = ["NEW", "OLD", "OLDER"]
                        except Exception as e:
                            # 오류 발생 시 기본 옵션 사용
                            status_options = ["NEW", "OLD", "OLDER"]
                        
                        # 현재 상태를 인덱스로 변환
                        current_status = part_data.get("status", "NEW")
                        try:
                            status_index = status_options.index(current_status)
                        except ValueError:
                            status_index = 0
                        
                        status = st.selectbox("상태*", status_options, index=status_index)
                        
                        min_stock = st.number_input("최소 재고량", min_value=0, value=part_data.get("min_stock", 0))
                        
                        # 현재 재고량 수정 필드 추가
                        current_quantity = st.number_input("현재 재고량", min_value=0, value=current_stock)
                    
                    description = st.text_area("설명", value=part_data.get("description", ""))
                    
                    # 저장 버튼을 명확하게 보이도록 col 사용하지 않고 전체 너비 사용
                    save_button = st.form_submit_button("✅ 저장", use_container_width=True)
                    
                    if save_button:
                        try:
                            # 현재 사용자 정보 가져오기
                            from utils.auth import get_current_user
                            current_user = get_current_user()
                            
                            # 업데이트할 기본 데이터만 준비 (최소한의 필수 필드만)
                            update_data = {
                                "part_name": part_name,
                                "unit": unit,
                                "status": status,
                                "updated_at": datetime.now().isoformat(),
                                "updated_by": current_user
                            }
                            
                            # 나머지 필드들을 조건부로 추가
                            if vietnamese_name:
                                update_data["vietnamese_name"] = vietnamese_name
                            if korean_name:
                                update_data["korean_name"] = korean_name
                            if spec:
                                update_data["spec"] = spec
                            if category:
                                update_data["category"] = category
                            if min_stock is not None:
                                update_data["min_stock"] = min_stock
                            if description:
                                update_data["description"] = description
                            
                            # 외부 모듈을 사용하여 업데이트 실행
                            update_result = update_part(selected_id, update_data)
                            
                            # 재고 정보 업데이트는 별도 처리
                            if current_quantity != current_stock:
                                # 외부 모듈을 사용하여 재고 업데이트
                                inventory_result = update_inventory(selected_id, current_quantity)
                            
                            # 결과 처리
                            if update_result["success"]:
                                display_success(f"부품 '{part_name}' 정보가 업데이트되었습니다.")
                                time.sleep(1)  # 잠시 대기 후 리로드
                                st.rerun()
                            else:
                                display_error(f"부품 정보 업데이트 실패: {update_result['message']}")
                        except Exception as e:
                            st.error(f"부품 정보 업데이트 중 오류가 발생했습니다: {e}")
                            st.error(f"오류 유형: {type(e).__name__}")
                            import traceback
                            st.error(f"상세 오류 내역: {traceback.format_exc()}")
                
                # 삭제 기능
                if st.button("🗑️ 부품 삭제"):
                    delete_confirm = st.checkbox(f"정말로 '{part_data.get('part_name')}' 부품을 삭제하시겠습니까?")
                    
                    if delete_confirm:
                        try:
                            # Supabase에서 삭제
                            result = supabase().from_("parts").delete().eq("part_id", selected_id).execute()
                            
                            if result.data:
                                display_success(f"부품 '{part_data.get('part_name')}'이(가) 삭제되었습니다.")
                                st.rerun()
                            else:
                                display_error("부품 삭제 중 오류가 발생했습니다.")
                        except Exception as e:
                            display_error(f"부품 삭제 중 오류가 발생했습니다: {e}")
            else:
                # 상세 정보 표시 (읽기 전용)
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("#### 기본 정보")
                    st.markdown(f"**부품 코드:** {part_data.get('part_code', '')}")
                    st.markdown(f"**부품명:** {part_data.get('part_name', '')}")
                    st.markdown(f"**베트남어명:** {part_data.get('vietnamese_name', '')}")
                    st.markdown(f"**한국어명:** {part_data.get('korean_name', '')}")
                    st.markdown(f"**사양:** {part_data.get('spec', '')}")
                    st.markdown(f"**단위:** {part_data.get('unit', '')}")
                    st.markdown(f"**카테고리:** {part_data.get('category', '')}")
                    st.markdown(f"**상태:** {part_data.get('status', '')}")
                
                with col2:
                    st.markdown("#### 관리 정보")
                    st.markdown(f"**최소 재고량:** {part_data.get('min_stock', 0)} {part_data.get('unit', '')}")
                    st.markdown(f"**현재 재고량:** {current_stock} {part_data.get('unit', '')}")
                    st.markdown(f"**생성일:** {part_data.get('created_at', '')}")
                    st.markdown(f"**수정일:** {part_data.get('updated_at', '')}")
            
            st.markdown("#### 설명")
            st.write(part_data.get('description', ''))
            
            # 가격 정보
            st.markdown("#### 공급업체별 가격 정보")
            try:
                # 가격 정보 조회 - 실제 part_prices 테이블과 임시 temp_part_prices 테이블을 모두 조회
                try:
                    # 1. 실제 part_prices 테이블 조회
                    price_result = supabase().from_("part_prices").select("""
                        price_id,
                        supplier_id,
                        unit_price,
                        currency,
                        effective_from,
                        is_current
                    """).eq("part_id", selected_id).gt("unit_price", 0).order("unit_price", desc=True).order("is_current", desc=True).order("effective_from", desc=True).execute()
                    
                    # 2. 임시 temp_part_prices 테이블 조회 - 있을 경우
                    try:
                        temp_price_result = supabase().from_("temp_part_prices").select("""
                            price_id,
                            supplier_id,
                            unit_price,
                            currency,
                            effective_from,
                            is_current
                        """).eq("part_id", selected_id).gt("unit_price", 0).execute()
                        
                        # 결과 병합 (임시 테이블 결과 추가)
                        if temp_price_result.data:
                            price_result.data.extend(temp_price_result.data)
                    except Exception as e:
                        # 임시 테이블이 없을 수 있으므로 오류는 무시
                        pass
                    
                    if price_result.data:
                        # 공급업체 정보 가져오기
                        supplier_ids = [item.get('supplier_id') for item in price_result.data if item.get('supplier_id')]
                        supplier_map = {}
                        
                        if supplier_ids:
                            supplier_result = supabase().from_("suppliers").select("supplier_id, supplier_name").in_("supplier_id", supplier_ids).execute()
                            if supplier_result.data:
                                supplier_map = {s.get('supplier_id'): s.get('supplier_name') for s in supplier_result.data}
                        
                        # 데이터 변환
                        price_data = []
                        for item in price_result.data:
                            supplier_id = item.get('supplier_id')
                            unit_price = item.get('unit_price')
                            # unit_price가 0보다 큰 경우만 표시
                            if unit_price is not None and unit_price > 0:
                                price_data.append({
                                    'price_id': item.get('price_id'),
                                    'supplier_name': supplier_map.get(supplier_id, 'Unknown'),
                                    'supplier_id': supplier_id,
                                    'unit_price': unit_price,
                                    'currency': item.get('currency'),
                                    'effective_date': item.get('effective_from'),
                                    'is_current': item.get('is_current')
                                })
                        
                        if price_data:
                            # 가격 정보 데이터 프레임 생성
                            price_df = pd.DataFrame(price_data)
                            
                            # 데이터프레임 표시
                            st.dataframe(
                                price_df,
                                column_config={
                                    'supplier_name': st.column_config.TextColumn("공급업체"),
                                    'unit_price': st.column_config.NumberColumn("단가", format="%d"),
                                    'currency': st.column_config.TextColumn("통화"),
                                    'effective_date': st.column_config.DateColumn("적용일", format="YYYY-MM-DD"),
                                    'is_current': st.column_config.CheckboxColumn("현재 적용")
                                },
                                use_container_width=True,
                                hide_index=True
                            )
                        else:
                            st.info("유효한 단가 정보가 없습니다.")
                    else:
                        st.info("등록된 가격 정보가 없습니다.")
                except Exception as e:
                    st.error(f"가격 정보를 불러오는 중 오류가 발생했습니다: {e}")
                
                # 가격 추가/수정 UI
                if "edit_price_info" in st.session_state:
                    st.markdown("#### 가격 정보 수정")
                    edit_info = st.session_state.edit_price_info
                    
                    with st.form("edit_price_form", clear_on_submit=False):
                        # 수정 대상 공급업체 표시
                        st.markdown(f"**공급업체:** {edit_info.get('supplier_name')}")
                        supplier_id = edit_info.get('supplier_id')
                        
                        # 가격 정보 입력 필드
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            unit_price = st.number_input("단가", min_value=0, value=int(edit_info.get('unit_price', 0)))
                        with col2:
                            currency_options = ["₫", "$", "€", "¥"]
                            curr_idx = 0
                            try:
                                curr_idx = currency_options.index(edit_info.get('currency'))
                            except (ValueError, TypeError):
                                curr_idx = 0
                            currency = st.selectbox("통화", currency_options, index=curr_idx)
                        with col3:
                            try:
                                default_date = datetime.strptime(edit_info.get('effective_date'), "%Y-%m-%d").date()
                            except (ValueError, TypeError):
                                default_date = datetime.now().date()
                            effective_date = st.date_input("적용일", value=default_date)
                        
                        is_current = st.checkbox("현재 적용", value=edit_info.get('is_current', True))
                        
                        # 두 버튼의 레이아웃 개선
                        col1, col2 = st.columns(2)
                        with col1:
                            submit_button = st.form_submit_button("✅ 가격 수정", use_container_width=True)
                            
                            if submit_button:
                                try:
                                    # 현재 사용자 정보
                                    from utils.auth import get_current_user
                                    current_user = get_current_user()
                                    
                                    # 수정할 데이터
                                    update_data = {
                                        "unit_price": unit_price,
                                        "currency": currency,
                                        "effective_from": effective_date.isoformat(),
                                        "is_current": unit_price > 0,  # 단가가 0보다 크면 TRUE, 아니면 FALSE
                                        "updated_at": datetime.now().isoformat(),
                                        "updated_by": current_user
                                    }
                                    
                                    # Supabase 업데이트
                                    update_result = supabase().from_("part_prices").update(update_data).eq("price_id", edit_info.get('price_id')).execute()
                                    
                                    if update_result.data:
                                        # 세션에서 수정 정보 제거
                                        st.session_state.pop('edit_price_info', None)
                                        display_success("가격 정보가 수정되었습니다.")
                                        st.rerun()
                                    else:
                                        display_error("가격 정보 수정 중 오류가 발생했습니다.")
                                except Exception as e:
                                    display_error(f"가격 정보 수정 중 오류가 발생했습니다: {e}")
                        
                        with col2:
                            cancel_button = st.form_submit_button("❌ 취소", use_container_width=True)
                            if cancel_button:
                                # 세션에서 수정 정보 제거
                                st.session_state.pop('edit_price_info', None)
                                st.rerun()
                else:
                    # 새 가격 정보 추가 UI
                    st.markdown("#### 새 가격 정보 추가")
                    with st.form("add_price_form", clear_on_submit=True):
                        # 공급업체 목록 조회
                        supplier_result = supabase().from_("suppliers").select("supplier_id, supplier_name").execute()
                        
                        if supplier_result.data:
                            supplier_options = [f"{s['supplier_name']}" for s in supplier_result.data]
                            supplier_ids = {s['supplier_name']: s['supplier_id'] for s in supplier_result.data}
                            
                            selected_supplier = st.selectbox("공급업체 선택", supplier_options)
                            currency_options = ["₫", "$", "€", "¥"]
                            
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                unit_price = st.number_input("단가", min_value=0, value=0)
                            with col2:
                                currency = st.selectbox("통화", currency_options, index=0)
                            with col3:
                                effective_date = st.date_input("적용일", datetime.now())
                            
                            is_current = st.checkbox("현재 적용", value=True)
                            
                            submit_button = st.form_submit_button("✅ 가격 추가", use_container_width=True)
                            
                            if submit_button:
                                try:
                                    # 현재 사용자 정보
                                    from utils.auth import get_current_user
                                    current_user = get_current_user()
                                    
                                    supplier_id = supplier_ids.get(selected_supplier)
                                    
                                    # 새 가격 데이터
                                    price_data = {
                                        "part_id": selected_id,
                                        "supplier_id": supplier_id,
                                        "unit_price": unit_price,
                                        "currency": currency,
                                        "effective_from": effective_date.isoformat(),
                                        "is_current": is_current,
                                        "created_by": current_user
                                    }
                                    
                                    # 새로 추가
                                    price_data["is_current"] = unit_price > 0  # 단가가 0보다 크면 TRUE, 아니면 FALSE
                                    try:
                                        # 직접 INSERT 대신 RPC 함수 사용
                                        rpc_result = supabase().rpc(
                                            "insert_part_price",
                                            {
                                                "p_part_id": selected_id,
                                                "p_supplier_id": supplier_id,
                                                "p_unit_price": unit_price,
                                                "p_currency": currency,
                                                "p_effective_from": effective_date.isoformat(),
                                                "p_is_current": unit_price > 0,
                                                "p_created_by": current_user
                                            }
                                        ).execute()
                                        
                                        if rpc_result.data and rpc_result.data.get('success'):
                                            display_success(f"새 가격 정보가 추가되었습니다.")
                                            st.rerun()
                                        else:
                                            error_msg = rpc_result.data.get('message') if rpc_result.data else "가격 정보 추가 중 오류가 발생했습니다."
                                            display_error(error_msg)
                                    except Exception as e:
                                        # 일반 오류 처리
                                        display_error(f"가격 정보 추가 중 오류가 발생했습니다: {e}")
                                except Exception as e:
                                    display_error(f"가격 정보 추가 중 오류가 발생했습니다: {e}")
                        else:
                            st.warning("등록된 공급업체가 없습니다. 먼저 공급업체를 등록해주세요.")
                            # 폼 submit 버튼 추가 (필수) - 빈 폼이라도 submit 버튼이 있어야 함
                            st.form_submit_button("➕ 공급업체 등록 필요", use_container_width=True)
            except Exception as e:
                st.error(f"가격 정보를 불러오는 중 오류가 발생했습니다: {e}")
            
            # 입출고 이력
            st.markdown("#### 최근 입출고 이력")
            
            # 탭으로 입고/출고 구분
            history_tabs = st.tabs(["입고 이력", "출고 이력"])
            
            # 입고 이력
            with history_tabs[0]:
                try:
                    # 입고 이력 조회
                    inbound_result = supabase().from_("inbound").select("""
                        inbound_id,
                        quantity,
                        unit_price,
                        total_price,
                        inbound_date,
                        reference_number,
                        created_at,
                        suppliers!inner(supplier_name),
                        users!inner(username)
                    """).eq("part_id", selected_id).order("inbound_date", desc=True).limit(10).execute()
                    
                    if inbound_result.data:
                        # 데이터 변환
                        inbound_data = []
                        for item in inbound_result.data:
                            inbound_data.append({
                                'inbound_id': item.get('inbound_id'),
                                'supplier_name': item.get('suppliers', {}).get('supplier_name'),
                                'quantity': item.get('quantity'),
                                'unit_price': item.get('unit_price'),
                                'total_price': item.get('total_price'),
                                'inbound_date': item.get('inbound_date'),
                                'reference_number': item.get('reference_number'),
                                'created_by': item.get('users', {}).get('username')
                            })
                        
                        inbound_df = pd.DataFrame(inbound_data)
                        
                        st.dataframe(
                            inbound_df,
                            column_config={
                                'inbound_id': st.column_config.TextColumn("입고 ID"),
                                'supplier_name': st.column_config.TextColumn("공급업체"),
                                'quantity': st.column_config.NumberColumn("수량", format="%d"),
                                'unit_price': st.column_config.NumberColumn("단가", format="%d"),
                                'total_price': st.column_config.NumberColumn("총액", format="%d"),
                                'inbound_date': st.column_config.DateColumn("입고일", format="YYYY-MM-DD"),
                                'reference_number': st.column_config.TextColumn("참조 번호"),
                                'created_by': st.column_config.TextColumn("등록자")
                            },
                            use_container_width=True,
                            hide_index=True
                        )
                    else:
                        st.info("입고 이력이 없습니다.")
                except Exception as e:
                    st.error(f"입고 이력을 불러오는 중 오류가 발생했습니다: {e}")
            
            # 출고 이력
            with history_tabs[1]:
                try:
                    # 출고 이력 조회
                    outbound_result = supabase().from_("outbound").select("""
                        outbound_id,
                        quantity,
                        outbound_date,
                        requestor,
                        department,
                        equipment_id,
                        reference_number,
                        purpose,
                        created_at,
                        users!inner(username)
                    """).eq("part_id", selected_id).order("outbound_date", desc=True).limit(10).execute()
                    
                    if outbound_result.data:
                        # 데이터 변환
                        outbound_data = []
                        for item in outbound_result.data:
                            outbound_data.append({
                                'outbound_id': item.get('outbound_id'),
                                'quantity': item.get('quantity'),
                                'outbound_date': item.get('outbound_date'),
                                'requestor': item.get('requestor'),
                                'department': item.get('department'),
                                'equipment_id': item.get('equipment_id'),
                                'purpose': item.get('purpose'),
                                'reference_number': item.get('reference_number'),
                                'created_by': item.get('users', {}).get('username')
                            })
                        
                        outbound_df = pd.DataFrame(outbound_data)
                        
                        st.dataframe(
                            outbound_df,
                            column_config={
                                'outbound_id': st.column_config.TextColumn("출고 ID"),
                                'quantity': st.column_config.NumberColumn("수량", format="%d"),
                                'outbound_date': st.column_config.DateColumn("출고일", format="YYYY-MM-DD"),
                                'requestor': st.column_config.TextColumn("요청자"),
                                'department': st.column_config.TextColumn("부서"),
                                'equipment_id': st.column_config.TextColumn("설비 ID"),
                                'purpose': st.column_config.TextColumn("용도"),
                                'reference_number': st.column_config.TextColumn("참조 번호"),
                                'created_by': st.column_config.TextColumn("등록자")
                            },
                            use_container_width=True,
                            hide_index=True
                        )
                    else:
                        st.info("출고 이력이 없습니다.")
                except Exception as e:
                    st.error(f"출고 이력을 불러오는 중 오류가 발생했습니다: {e}")
        except Exception as e:
            display_error(f"부품 상세 정보를 불러오는 중 오류가 발생했습니다: {e}")

if __name__ == "__main__":
    show() 