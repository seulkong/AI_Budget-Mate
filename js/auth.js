const API_BASE_URL = 'https://ai-budget-mate-api.cana1222.workers.dev'; // Cloudflare Workers 주소

document.addEventListener('DOMContentLoaded', () => {
    // 이미 프로필 설정을 마쳤다면 홈으로 이동
    const pathname = window.location.pathname;
    if (pathname.endsWith('index.html') || pathname.endsWith('signup.html') || pathname.endsWith('/')) {
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

            // 고유 ID 생성 (단순 세션 관리용)
            const id = 'user_' + Date.now();

            // 세션 데이터 저장 (로그인 절차 생략)
            const userData = { id, name, style: consumptionStyle };
            localStorage.setItem('loggedInUser', JSON.stringify(userData));

            // 설문조사 페이지로 이동
            localStorage.setItem('tempUser', name);
            localStorage.setItem('tempUserId', id);
            window.location.href = 'survey.html';
        });
    }
});