const API_BASE_URL = 'https://ai-budget-mate-api.cana1222.workers.dev'; // Cloudflare Workers 주소

document.addEventListener('DOMContentLoaded', () => {
    try {
        const loggedInUserStr = localStorage.getItem('loggedInUser');
        if (!loggedInUserStr) {
            alert("로그 정보가 없습니다. 첫 화면으로 돌아갑니다.");
            window.location.href = 'index.html';
            return;
        }

        const loggedInUser = JSON.parse(loggedInUserStr);
        document.getElementById('userName').textContent = loggedInUser.name || "사용자";
        document.getElementById('userName2').textContent = loggedInUser.name || "사용자";

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
            } else {
                cardNameSelect.style.display = 'block';
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
            
            try {
                const storeEl = surveyForm.querySelector('input[name="store"]:checked');
                const carrierEl = surveyForm.querySelector('input[name="carrier"]:checked');
                const tierEl = surveyForm.querySelector('input[name="carrier_tier"]:checked');

                if (!storeEl || !carrierEl || !tierEl) {
                    alert("모든 설문 항목에 답해 주세요!");
                    return;
                }

                const store = storeEl.value;
                const carrier = carrierEl.value;
                const carrier_tier = tierEl.value;
                let card = 'none';
                if (cardIssuerSelect.value !== 'none' && cardIssuerSelect.value !== '') {
                    card = cardNameSelect.value || 'none';
                }

                // 정보 업데이트
                loggedInUser.store = store;
                loggedInUser.carrier = carrier;
                loggedInUser.carrier_tier = carrier_tier;
                loggedInUser.card = card;
                
                localStorage.setItem('loggedInUser', JSON.stringify(loggedInUser));

                // 서버 동기화 시도 (실패해도 페이지는 넘어가게 함)
                fetch(`${API_BASE_URL}/api/survey`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        id: loggedInUser.id,
                        store: store,
                        carrier: carrier
                    })
                }).catch(err => console.log('Sync skipped'));

                // 즉시 홈으로 이동
                window.location.replace('home.html');
            } catch (err) {
                alert("제출 중 오류가 발생했습니다: " + err.message);
            }
        });
    } catch (err) {
        alert("페이지 로드 중 오류가 발생했습니다: " + err.message);
    }
});