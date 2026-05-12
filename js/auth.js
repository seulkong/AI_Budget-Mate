document.addEventListener('DOMContentLoaded', () => {
    // 로그인 상태 확인 후 home.html로 리디렉션
    if (window.location.pathname.endsWith('index.html') || window.location.pathname.endsWith('signup.html')) {
        const loggedInUser = localStorage.getItem('loggedInUser');
        if (loggedInUser) {
            window.location.href = 'home.html';
        }
    }

    const signupForm = document.getElementById('signupForm');
    if (signupForm) {
        signupForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const name = document.getElementById('name').value;
            const phone = document.getElementById('phone').value;
            const id = document.getElementById('signupId').value;
            const password = document.getElementById('signupPassword').value;
            const confirmPassword = document.getElementById('confirmPassword').value;
            const messageEl = document.getElementById('signupMessage');

            if (password !== confirmPassword) {
                messageEl.textContent = '비밀번호가 일치하지 않습니다.';
                return;
            }

            // 실제로는 서버로 보내야 함. 여기서는 localStorage 사용.
            const users = JSON.parse(localStorage.getItem('users')) || {};
            if (users[id]) {
                messageEl.textContent = '이미 존재하는 ID입니다.';
                return;
            }

            users[id] = { name, phone, password };
            localStorage.setItem('users', JSON.stringify(users));
            
            // 회원가입 성공 시, 임시로 사용자 이름 저장 후 설문조사로 이동
            localStorage.setItem('tempUser', name);
            window.location.href = 'survey.html';
        });
    }

    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const id = document.getElementById('loginId').value;
            const password = document.getElementById('loginPassword').value;
            const messageEl = document.getElementById('loginMessage');

            const users = JSON.parse(localStorage.getItem('users')) || {};
            if (users[id] && users[id].password === password) {
                // 로그인 성공
                localStorage.setItem('loggedInUser', JSON.stringify({ id: id, name: users[id].name }));
                window.location.href = 'home.html';
            } else {
                messageEl.textContent = 'ID 또는 비밀번호가 올바르지 않습니다.';
            }
        });
    }
});