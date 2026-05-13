const API_BASE_URL = 'https://time-2xjx.onrender.com'; // 배포 시 'https://time-2xjx.onrender.com' 로 변경

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

    const surveyForm = document.getElementById('surveyForm');
    surveyForm.addEventListener('submit', (e) => {
        e.preventDefault();
        
        const store = surveyForm.querySelector('input[name="store"]:checked').value;
        const carrier = surveyForm.querySelector('input[name="carrier"]:checked').value;

        fetch(`${API_BASE_URL}/api/survey`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: tempUserId, store, carrier })
        })
        .then(res => res.json().then(data => ({ status: res.status, body: data })))
        .then(data => {
            if (data.status === 200) {
                // 로그인 상태로 전환
                localStorage.setItem('loggedInUser', JSON.stringify({ id: tempUserId, name: tempUser }));
                localStorage.removeItem('tempUser');
                localStorage.removeItem('tempUserId');
                window.location.href = 'home.html';
            } else {
                alert(data.body.error || '오류가 발생했습니다. 다시 시도해주세요.');
            }
        })
        .catch(err => {
            console.error('Survey error:', err);
            alert('서버와 통신할 수 없습니다.');
        });
    });
});