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
                // 권한 거부 등 실패 시 기본 위치(종로구) 사용
                fetchNearbyStores(37.5700, 126.9796);
            },
            {
                enableHighAccuracy: true,
                timeout: 10000,
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

    // 로딩 메시지 표시
    addMessageToChat('bot', '최적의 할인 정보를 찾고 있습니다...');

    // 사용자 정보 가져오기 (설문조사 결과)
    const loggedInUser = JSON.parse(localStorage.getItem('loggedInUser'));
    // 백엔드 API에 요청 보내기 (API_BASE_URL은 auth.js 등에 선언되어 있음, 없으면 하드코딩)
    const serverUrl = 'https://time-2xjx.onrender.com/search'; // 배포 시 'https://time-2xjx.onrender.com/search' 로 변경
    
    fetch(serverUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
            item_name: messageText,
            user_id: loggedInUser.id
        }),
    })
    .then(response => response.json())
    .then(data => {
        // 이전에 표시된 '로딩 메시지'를 찾아 제거
        const chatWindow = document.querySelector('.chat-window');
        const loadingMessage = Array.from(chatWindow.querySelectorAll('.bot-message')).pop();
        if (loadingMessage && loadingMessage.textContent.includes('찾고 있습니다')) {
            loadingMessage.remove();
        }

        // 서버로부터 받은 데이터 처리
        if (data.message) {
            addMessageToChat('bot', data.message);
        } else if (data.length > 0) {
            let reply = `'${messageText}'에 대한 추천 조합입니다:\n\n`;
            
            const events = data.filter(d => d.type === '행사 정보');
            const telecoms = data.filter(d => d.type === '통신사 할인');
            const cards = data.filter(d => d.type === '카드 혜택');

            if (events.length > 0) {
                reply += "🛒 편의점 행사:\n";
                events.forEach(e => {
                    reply += `- ${e.store}: ${e.item_name} (${e.event})\n`;
                });
                reply += "\n";
            }

            if (telecoms.length > 0) {
                reply += "📱 통신사 할인 (선호 편의점 기준):\n";
                telecoms.forEach(t => {
                    reply += `- ${t.telecom}: ${t.benefit}\n`;
                });
                reply += "\n";
            }
            
            if (cards.length > 0) {
                reply += "💳 함께 쓰면 좋은 카드:\n";
                // 카드 혜택은 너무 많을 수 있으므로 일부만 표시
                const cardLimit = 3;
                cards.slice(0, cardLimit).forEach(c => {
                    reply += `- ${c.card_name} (${c.store}): ${c.benefit}\n`;
                });
                if (cards.length > cardLimit) {
                    reply += `...등 ${cards.length - cardLimit}개의 추가 혜택이 있습니다.\n`;
                }
            }
            
            addMessageToChat('bot', reply);
        } else {
            addMessageToChat('bot', '검색 결과가 없습니다.');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        addMessageToChat('bot', '오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
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