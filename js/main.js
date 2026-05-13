// 탭 기능
function openTab(evt, tabName) {
    var i, tabcontent, tablinks;
    tabcontent = document.getElementsByClassName("tab-content");
    for (i = 0; i < tabcontent.length; i++) {
        tabcontent[i].style.display = "none";
    }
    tablinks = document.getElementsByClassName("tab-link");
    for (i = 0; i < tablinks.length; i++) {
        tablinks[i].className = tablinks[i].className.replace(" active", "");
    }
    document.getElementById(tabName).style.display = "block";
    evt.currentTarget.className += " active";
}

// 사용자 위치 가져오기
function getUserLocation() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            (position) => {
                const latitude = position.coords.latitude;
                const longitude = position.coords.longitude;
                console.log(`내 위치: 위도: ${latitude}, 경도: ${longitude}`);
                // 위치 정보를 기반으로 편의점 목록 가져오기
                fetchNearbyStores(latitude, longitude);
            },
            (error) => {
                console.error("위치 정보를 가져오는 데 실패했습니다.", error);
                alert("현재 위치를 가져올 수 없어 기본 위치(종로구)로 설정합니다. 브라우저의 위치 권한 설정을 확인해 주세요!");
                // 권한 거부 등 실패 시 기본 위치(종로구) 사용
                fetchNearbyStores(37.5700, 126.9796);
            },
            {
                enableHighAccuracy: true,
                timeout: 15000, // 시간을 15초로 늘림
                maximumAge: 0
            }
        );
    } else {
        alert("이 브라우저는 위치 정보를 지원하지 않습니다.");
        fetchNearbyStores(37.5700, 126.9796);
    }
}



// 근처 편의점 목록 가져오기
async function fetchNearbyStores(latitude, longitude) {
    let map = null;
    try {
        // 카카오 지도 SDK가 로드되었다면 지도 표시
        const mapContainer = document.getElementById('map-view');
        if (mapContainer && typeof kakao !== 'undefined' && kakao.maps) {
            const mapOption = {
                center: new kakao.maps.LatLng(latitude, longitude),
                level: 4,
            };
            map = new kakao.maps.Map(mapContainer, mapOption);

            // 사용자 위치 마커
            new kakao.maps.Marker({
                position: new kakao.maps.LatLng(latitude, longitude),
                map: map
            });
        }
    } catch (e) {
        console.warn('지도 로드 실패 (API 키 도메인 문제 등). 지도는 생략하고 리스트만 표시합니다.', e);
    }

    const REST_API_KEY = '28927acb4f3229bf2bddf11261cc6ff3';
    
    try {
        // 카카오 로컬 REST API로 편의점(CS2) 검색 (반경 1000m, 거리순)
        const url = `https://dapi.kakao.com/v2/local/search/category.json?category_group_code=CS2&x=${longitude}&y=${latitude}&radius=1000&sort=distance`;
        const response = await fetch(url, {
            headers: { 'Authorization': `KakaoAK ${REST_API_KEY}` }
        });
        
        if (!response.ok) throw new Error('API 요청 실패');
        
        const data = await response.json();
        
        const gs25List = document.getElementById('gs25-list');
        const cuList = document.getElementById('cu-list');
        if (gs25List) gs25List.innerHTML = '';
        if (cuList) cuList.innerHTML = '';

        if (data && data.documents) {
            data.documents.forEach(place => {
                const name = place.place_name.toUpperCase();
                if (name.includes('GS25') && gs25List) {
                    displayPlace(place, gs25List, map);
                } else if (name.includes('CU') && cuList) {
                    displayPlace(place, cuList, map);
                }
            });
            
            if (gs25List && gs25List.children.length === 0) gs25List.innerHTML = '<li>주변에 GS25가 없습니다.</li>';
            if (cuList && cuList.children.length === 0) cuList.innerHTML = '<li>주변에 CU가 없습니다.</li>';
        }
    } catch (error) {
        console.error("편의점 정보를 가져오는 데 실패했습니다.", error);
    }
}

function displayPlace(place, listElement, map) {
    listElement.style.padding = '0';
    listElement.style.margin = '0';

    const distanceText = place.distance >= 1000 ? (place.distance / 1000).toFixed(1) + 'km' : place.distance + 'm';

    const listItem = document.createElement('li');
    listItem.style.padding = '15px';
    listItem.style.border = '1px solid #ddd';
    listItem.style.borderRadius = '8px';
    listItem.style.marginBottom = '10px';
    listItem.style.backgroundColor = 'white';
    listItem.style.listStyle = 'none';
    listItem.style.boxShadow = '0 2px 4px rgba(0,0,0,0.05)';
    listItem.style.transition = 'transform 0.2s';
    
    listItem.addEventListener('mouseenter', () => listItem.style.transform = 'translateY(-2px)');
    listItem.addEventListener('mouseleave', () => listItem.style.transform = 'translateY(0)');
    listItem.style.cursor = 'pointer';
    listItem.addEventListener('click', () => openMapModal(place.place_name, place.y, place.x));

    listItem.innerHTML = `
        <h4 style="margin: 0 0 8px 0; color: #4F46E5; font-size: 1.1em;">${place.place_name}</h4>
        <p style="margin: 4px 0; font-weight: bold; color: #EF4444; font-size: 0.9em;">📍 거리: ${distanceText}</p>
        <p style="margin: 4px 0; color: #666; font-size: 0.85em;">🏠 ${place.road_address_name || place.address_name}</p>
        ${place.phone ? `<p style="margin: 4px 0; color: #666; font-size: 0.85em;">📞 ${place.phone}</p>` : ''}
    `;
    listElement.appendChild(listItem);

    // 지도가 정상적으로 렌더링된 경우에만 마커 표시
    if (map && typeof kakao !== 'undefined' && kakao.maps) {
        const marker = new kakao.maps.Marker({
            map: map,
            position: new kakao.maps.LatLng(place.y, place.x)
        });

        kakao.maps.event.addListener(marker, 'click', function() {
            const infowindow = new kakao.maps.InfoWindow({ zIndex: 1 });
            infowindow.setContent('<div style="padding:5px;font-size:12px;color:#333;">' + place.place_name + '</div>');
            infowindow.open(map, marker);
        });
    }
}

// 구글 지도 모달 열기
function openMapModal(placeName, lat, lng) {
    const modal = document.getElementById('mapModal');
    const title = document.getElementById('mapModalTitle');
    const mapContainer = document.getElementById('modal-map-view');
    
    if (!modal || !mapContainer) return;
    
    title.textContent = placeName;
    modal.style.display = 'block';

    // 구글 지도 무료 임베드(iframe) 방식 사용
    const iframeHtml = `<iframe 
        width="100%" 
        height="100%" 
        frameborder="0" 
        style="border:0;" 
        src="https://maps.google.com/maps?q=${lat},${lng}&hl=ko&z=17&output=embed" 
        allowfullscreen>
    </iframe>`;
    
    mapContainer.innerHTML = iframeHtml;
}

// 지도 모달 닫기
function closeMapModal() {
    const modal = document.getElementById('mapModal');
    const mapContainer = document.getElementById('modal-map-view');
    if (modal) {
        modal.style.display = 'none';
    }
    // 모달 닫을 때 iframe 비우기 (메모리 절약)
    if (mapContainer) {
        mapContainer.innerHTML = '';
    }
}

// 채팅 메시지를 화면에 추가하는 함수
function addMessageToChat(sender, text) {
    const chatWindow = document.querySelector('.chat-window');
    
    const messageElement = document.createElement('div');
    messageElement.classList.add('chat-message', `${sender}-message`);
    
    // --- 수정된 부분 ---
    // 1. 받은 텍스트의 줄바꿈 문자(\n)를 HTML 줄바꿈 태그(<br>)로 변경합니다.
    const formattedText = text.replace(/\n/g, '<br>');
    // 2. textContent 대신 innerHTML을 사용하여 <br> 태그가 적용되도록 합니다.
    messageElement.innerHTML = formattedText;
    // --------------------
    
    chatWindow.appendChild(messageElement);
    chatWindow.scrollTop = chatWindow.scrollHeight; // 항상 최신 메시지가 보이도록 스크롤
}

// 메시지 전송 기능
function sendMessage() {
    const chatInput = document.getElementById('chatInput');
    const messageText = chatInput.value.trim();
    if (messageText === '') return;

    addMessageToChat('user', messageText);
    chatInput.value = '';

    // 잡담 및 일상 대화 예외 처리 (Fallback)
    const smallTalkKeywords = ['안녕', '고마워', '누구야', '반가워', '안뇽', '감사', '누구니', 'ㅎㅇ'];
    const isSmallTalk = smallTalkKeywords.some(keyword => messageText.includes(keyword));

    if (isSmallTalk && messageText.length < 15) {
        addMessageToChat('bot', '저는 편의점 할인 정보를 찾아주는 Young-AI 파트너입니다! 잡담보다는 편의점 할인을 기가 막히게 잘 찾으니, 언제든 찾고 싶은 상품이 있다면 편하게 말씀해 주세요!');
        return;
    }

    // 로딩 메시지 표시
    addMessageToChat('bot', '최적의 할인 정보를 찾고 있습니다...');

    // 사용자 정보 가져오기 (설문조사 결과)
    const loggedInUser = JSON.parse(localStorage.getItem('loggedInUser'));
    if (!loggedInUser) {
        alert("사용자 정보가 없습니다. 다시 시작해 주세요!");
        window.location.href = 'index.html';
        return;
    }

    const serverUrl = 'https://ai-budget-mate-api.cana1222.workers.dev/search'; // Cloudflare Workers 주소
    
    fetch(serverUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ 
            item_name: messageText,
            user_style: loggedInUser.style || 'health',
            user_store: loggedInUser.store || 'GS25',
            user_telecom: loggedInUser.carrier || 'none',
            user_telecom_tier: loggedInUser.carrier_tier || 'none',
            user_card: loggedInUser.card || 'none'
        }),
    })
    .then(response => {
        if (!response.ok) throw new Error('서버 응답 오류: ' + response.status);
        return response.json();
    })
    .then(data => {
        // 이전에 표시된 '로딩 메시지'를 찾아 제거
        const chatWindow = document.querySelector('.chat-window');
        const loadingMessage = Array.from(chatWindow.querySelectorAll('.bot-message')).pop();
        if (loadingMessage && loadingMessage.textContent.includes('찾고 있습니다')) {
            loadingMessage.remove();
        }

        // 서버로부터 받은 데이터 처리
        if (data.type === 'list') {
            addMessageToChat('bot', data.message);
            const chatWindow = document.querySelector('.chat-window');
            const optionsContainer = document.createElement('div');
            optionsContainer.style.display = 'flex';
            optionsContainer.style.flexWrap = 'wrap';
            optionsContainer.style.gap = '8px';
            optionsContainer.style.marginTop = '10px';
            optionsContainer.style.padding = '0 10px';
            
            data.options.forEach(option => {
                const btn = document.createElement('button');
                btn.textContent = option;
                btn.className = 'option-btn';
                btn.style.padding = '8px 14px';
                btn.style.border = '1px solid #007bff';
                btn.style.borderRadius = '20px';
                btn.style.backgroundColor = 'white';
                btn.style.color = '#007bff';
                btn.style.cursor = 'pointer';
                btn.style.fontSize = '0.85em';
                btn.style.margin = '4px';
                btn.style.transition = 'all 0.2s';

                btn.onclick = () => {
                    document.getElementById('chatInput').value = option;
                    sendMessage();
                };
                optionsContainer.appendChild(btn);
            });
            chatWindow.appendChild(optionsContainer);
            chatWindow.scrollTop = chatWindow.scrollHeight;
        } else if (data.type === 'result') {
            addMessageToChat('bot', data.message);
            
            // 근처 편의점 찾기 버튼 추가
            const chatWindow = document.querySelector('.chat-window');
            const mapLinkBtn = document.createElement('button');
            mapLinkBtn.textContent = `📍 근처 ${data.shop} 찾기`;
            mapLinkBtn.className = 'map-link-btn';
            mapLinkBtn.style.margin = '10px 10px 20px 10px';
            mapLinkBtn.style.padding = '10px 20px';
            mapLinkBtn.style.backgroundColor = '#28a745';
            mapLinkBtn.style.color = 'white';
            mapLinkBtn.style.border = 'none';
            mapLinkBtn.style.borderRadius = '25px';
            mapLinkBtn.style.cursor = 'pointer';
            mapLinkBtn.style.fontWeight = 'bold';
            mapLinkBtn.style.fontSize = '0.95em';
            mapLinkBtn.style.transition = 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
            mapLinkBtn.style.boxShadow = '0 4px 12px rgba(40, 167, 69, 0.3)';
            
            mapLinkBtn.onmouseover = () => {
                mapLinkBtn.style.transform = 'translateY(-2px)';
                mapLinkBtn.style.boxShadow = '0 6px 15px rgba(40, 167, 69, 0.4)';
                mapLinkBtn.style.backgroundColor = '#218838';
            };
            mapLinkBtn.onmouseout = () => {
                mapLinkBtn.style.transform = 'translateY(0)';
                mapLinkBtn.style.boxShadow = '0 4px 12px rgba(40, 167, 69, 0.3)';
                mapLinkBtn.style.backgroundColor = '#28a745';
            };

            mapLinkBtn.onclick = () => {
                // 1. 지도 탭 보이기 및 전환
                const mapTab = document.getElementById('Map');
                const chatbotTab = document.getElementById('Chatbot');
                
                if (mapTab && chatbotTab) {
                    chatbotTab.style.display = 'none'; // 챗봇 숨기기
                    mapTab.style.display = 'block';    // 지도 보이기
                    
                    // 탭 메뉴가 혹시 필요할 수 있으니 보이게 처리
                    const tabMenu = document.querySelector('.tab-menu');
                    if (tabMenu) tabMenu.style.display = 'flex';
                    
                    // 탭 링크 활성화 상태 변경
                    document.querySelectorAll('.tab-link').forEach(link => {
                        if (link.textContent.includes('찾기')) link.classList.add('active');
                        else link.classList.remove('active');
                    });
                }
                
                // 2. 해당 브랜드만 강조 (스마트 필터링)
                const gs25Col = Array.from(document.querySelectorAll('.store-column')).find(el => el.querySelector('#gs25-list'));
                const cuCol = Array.from(document.querySelectorAll('.store-column')).find(el => el.querySelector('#cu-list'));
                const container = document.querySelector('.store-list-container');
                
                if (container) {
                    container.style.display = 'flex';
                    container.style.flexDirection = 'column'; // 필터링 시에는 세로로 크게 보기
                }
                
                if (data.shop === 'GS25') {
                    if (gs25Col) {
                        gs25Col.style.display = 'block';
                        gs25Col.style.width = '100%';
                        gs25Col.style.border = '2px solid #007bff';
                        gs25Col.style.borderRadius = '15px';
                        gs25Col.style.padding = '15px';
                        gs25Col.style.marginBottom = '20px';
                    }
                    if (cuCol) cuCol.style.display = 'none';
                } else if (data.shop === 'CU') {
                    if (cuCol) {
                        cuCol.style.display = 'block';
                        cuCol.style.width = '100%';
                        cuCol.style.border = '2px solid #007bff';
                        cuCol.style.borderRadius = '15px';
                        cuCol.style.padding = '15px';
                        cuCol.style.marginBottom = '20px';
                    }
                    if (gs25Col) gs25Col.style.display = 'none';
                }
                
                // 필터 초기화 버튼 추가 (작고 깔끔한 디자인으로 변경)
                let resetBtn = document.getElementById('filterResetBtn');
                if (!resetBtn) {
                    resetBtn = document.createElement('button');
                    resetBtn.id = 'filterResetBtn';
                    resetBtn.textContent = '🔄 모든 편의점 다시 보기';
                    resetBtn.style.display = 'block';
                    resetBtn.style.margin = '20px auto';
                    resetBtn.style.padding = '12px 24px';
                    resetBtn.style.backgroundColor = '#007bff';
                    resetBtn.style.color = 'white';
                    resetBtn.style.border = 'none';
                    resetBtn.style.borderRadius = '30px';
                    resetBtn.style.cursor = 'pointer';
                    resetBtn.style.fontWeight = 'bold';
                    resetBtn.style.boxShadow = '0 4px 15px rgba(0, 123, 255, 0.3)';
                    
                    resetBtn.onclick = () => {
                        if (container) container.style.flexDirection = 'row';
                        if (gs25Col) {
                            gs25Col.style.display = 'block';
                            gs25Col.style.border = 'none';
                            gs25Col.style.width = '50%';
                        }
                        if (cuCol) {
                            cuCol.style.display = 'block';
                            cuCol.style.border = 'none';
                            cuCol.style.width = '50%';
                        }
                        resetBtn.remove();
                    };
                    container.parentNode.appendChild(resetBtn);
                }
            };
            
            chatWindow.appendChild(mapLinkBtn);
            chatWindow.scrollTop = chatWindow.scrollHeight;
        } else if (data.message) {
            addMessageToChat('bot', data.message);
        } else {
            addMessageToChat('bot', '원하시는 정보를 찾지 못했습니다.');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('서버 연결 실패: ' + error.message);
        addMessageToChat('bot', '앗, 잠시 정보를 불러오는 데 문제가 생겼어요. 네트워크 연결을 확인하시고 1~2분 뒤에 다시 시도해 주세요!');
    });
}

// 페이지 로드 시 실행
document.addEventListener('DOMContentLoaded', () => {
    // 로그인 상태 확인
    const loggedInUserStr = localStorage.getItem('loggedInUser');
    if (!loggedInUserStr) {
        window.location.href = 'index.html';
        return;
    }
    const loggedInUser = JSON.parse(loggedInUserStr);
    document.getElementById('homeUserName').textContent = loggedInUser.name;

    let greetingMsg = `안녕하세요, ${loggedInUser.name}님! 원하시는 편의점 상품을 입력해 주시면 최적의 구매 방법을 찾아드릴게요. (예: 오레오씬즈화이트, 우유)`;
    if (loggedInUser.style === 'health') {
        greetingMsg = `안녕하세요! 건강과 맛을 모두 챙기시는군요. 칼로리는 낮고 영양은 빵빵한 헬스케어 상품 위주로 추천해 드릴게요!`;
    } else if (loggedInUser.style === 'dessert') {
        greetingMsg = `안녕하세요! 달콤한 휴식이 필요하신가요? 보기만 해도 기분 좋아지는 편의점 디저트와 달달한 간식들을 찾아드릴게요!`;
    } else if (loggedInUser.style === 'brand') {
        const storeStr = loggedInUser.store && loggedInUser.store !== 'none' ? loggedInUser.store : '선호하시는 편의점';
        greetingMsg = `안녕하세요! ${storeStr}에서 진행 중인 쏠쏠한 혜택을 중심으로 찾아드릴게요. 찾으시는 상품이 있나요?`;
    } else if (loggedInUser.style === 'trend') {
        greetingMsg = `안녕하세요! 트렌디한 감각을 지니셨군요. 요즘 SNS에서 가장 핫한 신상과 트렌디한 편의점 상품 위주로 추천해 드릴게요!`;
    }

    // 성향별 가이드 문구 설정
    let guideStyle = "맞춤형";
    if (loggedInUser.style === 'health') guideStyle = "건강한 헬시 플레저";
    else if (loggedInUser.style === 'dessert') guideStyle = "달콤한 디저트";
    else if (loggedInUser.style === 'brand') guideStyle = `${loggedInUser.store && loggedInUser.store !== 'none' ? loggedInUser.store : '편의점'}의 대박 1+1`;
    else if (loggedInUser.style === 'trend') guideStyle = "가장 핫한 트렌드";

    // 작성 가이드 추가
    greetingMsg += `<br><br>[작성 가이드]<br>1. '우유', '라면'처럼 상품의 종류를 입력하시면 행사 중인 전체 리스트를 보여드려요.<br>2. '오레오씬즈화이트', '신라면'처럼 특정 상품명을 입력하시면 가장 저렴하게 살 수 있는 최적의 할인 조합을 즉시 찾아드립니다!`;
    greetingMsg += `<br>3. '추천해줘' 혹은 '요즘 핫한 거 뭐야?'라고 채팅해서 ${guideStyle} 상품들을 추천받아보세요!`;
    
    // HTML에 하드코딩된 인사말 교체
    const initialBotMessage = document.querySelector('.chat-window .bot-message');
    if (initialBotMessage) {
        initialBotMessage.innerHTML = greetingMsg.replace(/\n/g, '<br>');
    }

    // 로그아웃 버튼
    document.getElementById('logoutButton').addEventListener('click', () => {
        localStorage.removeItem('loggedInUser');
        window.location.href = 'index.html';
    });

    // --- 챗봇 이벤트 리스너 추가 ---
    const chatInput = document.getElementById('chatInput');
    const chatSendButton = document.getElementById('chatSendButton');

    chatSendButton.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
    // ---------------------------------

    // 사용자 위치 기반으로 편의점 목록 가져오기
    getUserLocation();
});