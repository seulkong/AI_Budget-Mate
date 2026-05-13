const API_BASE_URL = 'https://time-2xjx.onrender.com'; // 배포 시 'https://time-2xjx.onrender.com' 로 변경
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
            const phone = document.getElementById('phone').value.trim();
            const id = document.getElementById('signupId').value.trim();
            const password = document.getElementById('signupPassword').value.trim();
            const confirmPassword = document.getElementById('confirmPassword').value.trim();
            const messageEl = document.getElementById('signupMessage');

            if (password !== confirmPassword) {
                messageEl.textContent = '비밀번호가 일치하지 않습니다.';
                return;
            }

            fetch(`${API_BASE_URL}/api/signup`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id, name, phone, password })
            })
            .then(res => res.json().then(data => ({ status: res.status, body: data })))
            .then(data => {
                if (data.status === 201) {
                    localStorage.setItem('tempUser', name);
                    localStorage.setItem('tempUserId', id);
                    window.location.href = 'survey.html';
                } else {
                    messageEl.textContent = data.body.error || '회원가입에 실패했습니다.';
                }
            })
            .catch(err => {
                console.error('Signup error:', err);
                messageEl.textContent = '서버와 통신할 수 없습니다.';
            });
        });
    }

    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const id = document.getElementById('loginId').value.trim();
            const password = document.getElementById('loginPassword').value.trim();
            const messageEl = document.getElementById('loginMessage');

            fetch(`${API_BASE_URL}/api/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id, password })
            })
            .then(res => res.json().then(data => ({ status: res.status, body: data })))
            .then(data => {
                if (data.status === 200) {
                    localStorage.setItem('loggedInUser', JSON.stringify(data.body.user));
                    window.location.href = 'home.html';
                } else {
                    messageEl.textContent = data.body.error || 'ID 또는 비밀번호가 올바르지 않습니다.';
                }
            })
            .catch(err => {
                console.error('Login error:', err);
                messageEl.textContent = '서버와 통신할 수 없습니다.';
            });
        });
    }
});