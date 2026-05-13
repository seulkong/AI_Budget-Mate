const API_BASE_URL = 'https://ai-budget-mate-api.cana1222.workers.dev'; // Cloudflare Workers 주소

document.addEventListener('DOMContentLoaded', () => {
    const tempUser = localStorage.getItem('tempUser');
    const tempUserId = localStorage.getItem('tempUserId');
    if (!tempUser || !tempUserId) {
        // 비정상 접근 시 로그인 페이지로
        window.location.href = 'index.html';
        return;
    }

    document.getElementById('userName').textContent = tempUser;
    document.getElementById('userName2').textContent = tempUser;

    const cardData = {
        '신한카드': ['Mr.Life (미스터 라이프)', 'Deep On Platinum+'],
        'KB국민카드': ['노리2 체크카드 (KB Pay)', '카카오뱅크 KB국민카드', '나라사랑카드'],
        '삼성카드': ['삼성 iD ON 카드', '삼성 iD SIMPLE 카드'],
        '현대카드': ['현대카드 Z work Edition2'],
        '롯데카드': ['LOCA LIKIT Shop'],
        '우리카드': ['D4 카드의정석 Ⅱ'],
        '하나카드': ['# MY WAY 카드'],
        '카카오뱅크': ['프렌즈 체크카드'],
        'NH농협카드': ['zgm.play 카드'],
        'GS리테일': ['GS 팝카드']
    };

    const cardIssuerSelect = document.getElementById('cardIssuer');
    const cardNameSelect = document.getElementById('cardName');

    cardIssuerSelect.addEventListener('change', () => {
        const issuer = cardIssuerSelect.value;
        cardNameSelect.innerHTML = '<option value="">카드 선택</option><option value="none">없음 / 목록에 없음</option>';
        
        if (issuer === 'none' || issuer === '') {
            cardNameSelect.style.display = 'none';
            cardNameSelect.required = false;
        } else {
            cardNameSelect.style.display = 'block';
            cardNameSelect.required = true;
            if (cardData[issuer]) {
                cardData[issuer].forEach(card => {
                    const option = document.createElement('option');
                    option.value = card;
                    option.textContent = card;
                    cardNameSelect.appendChild(option);
                });
            }
        }
    });

    const surveyForm = document.getElementById('surveyForm');
    surveyForm.addEventListener('submit', (e) => {
        e.preventDefault();
        
        const store = surveyForm.querySelector('input[name="store"]:checked').value;
        const carrier = surveyForm.querySelector('input[name="carrier"]:checked').value;
        const carrier_tier = surveyForm.querySelector('input[name="carrier_tier"]:checked').value;
        let card = 'none';
        if (cardIssuerSelect.value !== 'none' && cardIssuerSelect.value !== '') {
            card = cardNameSelect.value;
        }

        // users DB에서 기존 데이터(소비 스타일 등) 가져오기
        const users = JSON.parse(localStorage.getItem('users')) || {};
        const currentUser = users[tempUserId] || {};

        // LocalStorage에 설문 데이터 저장 (API 우회)
        const loggedInUser = {
            id: tempUserId,
            name: tempUser,
            style: currentUser.style, // 소비 스타일 추가
            store: store,
            carrier: carrier,
            carrier_tier: carrier_tier,
            card: card
        };
        
        localStorage.setItem('loggedInUser', JSON.stringify(loggedInUser));
        localStorage.removeItem('tempUser');
        localStorage.removeItem('tempUserId');
        
        // users DB에도 업데이트
        if (users[tempUserId]) {
            users[tempUserId].store = store;
            users[tempUserId].carrier = carrier;
            users[tempUserId].carrier_tier = carrier_tier;
            users[tempUserId].card = card;
            localStorage.setItem('users', JSON.stringify(users));
        }

        window.location.href = 'home.html';
    });
});