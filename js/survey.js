document.addEventListener('DOMContentLoaded', () => {
    const tempUser = localStorage.getItem('tempUser');
    if (!tempUser) {
        // 비정상 접근 시 로그인 페이지로
        window.location.href = 'index.html';
        return;
    }

    document.getElementById('userName').textContent = tempUser;
    document.getElementById('userName2').textContent = tempUser;

    const surveyForm = document.getElementById('surveyForm');
    surveyForm.addEventListener('submit', (e) => {
        e.preventDefault();
        
        const store = surveyForm.querySelector('input[name="store"]:checked').value;
        const carrier = surveyForm.querySelector('input[name="carrier"]:checked').value;

        // 설문조사 결과를 사용자 정보와 함께 저장
        const users = JSON.parse(localStorage.getItem('users')) || {};
        const loggedInUser = Object.values(users).find(user => user.name === tempUser);
        
        if (loggedInUser) {
            const userId = Object.keys(users).find(key => users[key] === loggedInUser);
            users[userId].survey = { store, carrier };
            localStorage.setItem('users', JSON.stringify(users));
            
            // 로그인 상태로 전환
            localStorage.setItem('loggedInUser', JSON.stringify({ id: userId, name: tempUser }));
            localStorage.removeItem('tempUser'); // 임시 정보 삭제
            
            window.location.href = 'home.html';
        } else {
            alert('오류가 발생했습니다. 다시 시도해주세요.');
            window.location.href = 'index.html';
        }
    });
});