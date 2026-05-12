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

                console.log(`위도: ${latitude}, 경도: ${longitude}`);
                // 위치 정보를 기반으로 편의점 목록 가져오기
                fetchNearbyStores(latitude, longitude);
            },
            (error) => {
                console.error("위치 정보를 가져오는 데 실패했습니다.", error);
                alert("위치 정보를 가져올 수 없습니다. 위치 서비스를 활성화해주세요.");
            }
        );
    } else {
        alert("이 브라우저는 위치 정보를 지원하지 않습니다.");
    }
}

// 근처 편의점 목록 가져오기
function fetchNearbyStores(latitude, longitude) {
    const mapContainer = document.getElementById('map-view'); // 지도를 표시할 div
    const mapOption = {
        center: new kakao.maps.LatLng(latitude, longitude), // 사용자 위치를 중심으로 설정
        level: 4, // 지도 확대 레벨
    };

    // 지도를 생성합니다
    const map = new kakao.maps.Map(mapContainer, mapOption);

    // 사용자 위치에 마커 표시
    const userMarker = new kakao.maps.Marker({
        position: new kakao.maps.LatLng(latitude, longitude),
        map: map
    });

    const places = new kakao.maps.services.Places();

    // 'GS25'와 'CU' 편의점 검색
    const keywords = ['GS25', 'CU'];
    keywords.forEach((keyword) => {
        places.keywordSearch(keyword, (data, status, pagination) => {
            if (status === kakao.maps.services.Status.OK) {
                const storeList = document.getElementById(`${keyword.toLowerCase()}-list`);
                storeList.innerHTML = ''; // 기존 목록 초기화

                for (let i = 0; i < data.length; i++) {
                    displayPlace(data[i], storeList, map);
                }
            } else {
                console.error(`${keyword} 검색 실패:`, status);
            }
        }, {
            location: new kakao.maps.LatLng(latitude, longitude),
            radius: 1000, // 검색 반경 (단위: 미터)
            sort: kakao.maps.services.SortBy.DISTANCE // 거리순 정렬
        });
    });
}

// 검색된 장소를 목록과 지도에 표시하는 함수
function displayPlace(place, listElement, map) {
    // 목록에 추가
    const listItem = document.createElement('li');
    listItem.textContent = `${place.place_name} (${place.distance}m)`;
    listElement.appendChild(listItem);

    // 지도에 마커 표시
    const marker = new kakao.maps.Marker({
        map: map,
        position: new kakao.maps.LatLng(place.y, place.x)
    });

    // 마커에 인포윈도우 표시
    kakao.maps.event.addListener(marker, 'click', function() {
        const infowindow = new kakao.maps.InfoWindow({
            zIndex: 1
        });
        infowindow.setContent('<div style="padding:5px;font-size:12px;">' + place.place_name + '</div>');
        infowindow.open(map, marker);
    });
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
    const users = JSON.parse(localStorage.getItem('users'));
    const userInfo = users[loggedInUser.id]?.survey || {};

    // 백엔드 API에 요청 보내기
    fetch('http://127.0.0.1:5001/search', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
            item_name: messageText,
            user_info: userInfo
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