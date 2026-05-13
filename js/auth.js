const API_BASE_URL = 'http://127.0.0.1:5001'; // 로컬 서버 주소
document.addEventListener('DOMContentLoaded', () => {
    // 로그인 상태 확인 후 home.html로 리디렉션
    const pathname = window.location.pathname;
    if (pathname.endsWith('index.html') || pathname.endsWith('signup.html') || pathname.endsWith('login.html') || pathname.endsWith('/')) {
        const loggedInUser = localStorage.getItem('loggedInUser');
        if (loggedInUser) {
            window.location.href = 'home.html';
        }
    }

    const signupForm = document.getElementById('signupForm');
    if (signupForm) {
        signupForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const name = document.getElementById('name').value.trim();
            const consumptionStyle = document.getElementById('consumptionStyle').value;
            const messageEl = document.getElementById('signupMessage');

            // 고유 ID 생성 (타임스탬프 + 랜덤 문자열)
            const id = 'user_' + Date.now() + '_' + Math.random().toString(36).substring(2, 9);

            // LocalStorage 기반 회원가입 로직
            const users = JSON.parse(localStorage.getItem('users')) || {};
            
            // 사용자 저장 (비밀번호 생략, 전화번호 대신 소비 스타일 저장)
            users[id] = { id, name, style: consumptionStyle };
            localStorage.setItem('users', JSON.stringify(users));

            // 임시 정보 저장 및 이동
            localStorage.setItem('tempUser', name);
            localStorage.setItem('tempUserId', id);
            window.location.href = 'survey.html';
        });
    }

    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const id = document.getElementById('loginId').value.trim();
            const password = document.getElementById('loginPassword').value.trim();
            const messageEl = document.getElementById('loginMessage');

            // LocalStorage 기반 로그인 로직
            const users = JSON.parse(localStorage.getItem('users')) || {};
            const user = users[id];

            if (user && user.password === password) {
                localStorage.setItem('loggedInUser', JSON.stringify({ 
                    id: user.id, 
                    name: user.name, 
                    phone: user.phone,
                    store: user.store,
                    carrier: user.carrier,
                    carrier_tier: user.carrier_tier,
                    card: user.card
                }));
                window.location.href = 'home.html';
            } else {
                messageEl.textContent = 'ID 또는 비밀번호가 올바르지 않습니다.';
            }
        });
    }
});