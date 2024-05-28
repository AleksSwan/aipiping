$(document).ready(function() {
    // Bootstrap form validation
    const form = document.getElementById('recommendation-form');

    form.addEventListener('submit', function(event) {
        event.preventDefault();
        event.stopPropagation();

        if (form.checkValidity()) {
            requestRecommendations();
        }

        form.classList.add('was-validated');
    }, false);

    function requestRecommendations() {
        const country = $('#country').val();
        const season = $('#season').val();
        const statusDiv = $('#status');
        const recommendationsDiv = $('#recommendations');

        statusDiv.html('<div class="alert alert-info">Requesting recommendations...</div>');
        recommendationsDiv.html('');

        fetch('http://localhost:3000/recommendations', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ country, season })
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => { throw new Error(err.detail); });
            }
            return response.json();
        })
        .then(data => {
            const uid = data.uid;
            checkStatus(uid);
        })
        .catch(error => {
            statusDiv.html(`<div class="alert alert-danger">Error: ${error.message}</div>`);
        });
    }

    function checkStatus(uid) {
        const statusDiv = $('#status');
        const recommendationsDiv = $('#recommendations');

        fetch(`http://localhost:3000/recommendations/${uid}`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'pending') {
                statusDiv.html('<div class="alert alert-info">Recommendations are being processed. Please wait...</div>');
                setTimeout(() => checkStatus(uid), 2000);
            } else if (data.status === 'completed') {
                statusDiv.html('<div class="alert alert-success">Recommendations received:</div>');
                recommendationsDiv.html(data.recommendations.map(rec => `<div class="recommendation alert alert-light">${rec}</div>`).join(''));
            } else if (data.status === 'error') {
                statusDiv.html(`<div class="alert alert-danger">Error: ${data.message}</div>`);
            } else {
                statusDiv.html(`<div class="alert alert-warning">Unknown status: ${data.status}</div>`);
            }
        })
        .catch(error => {
            statusDiv.html(`<div class="alert alert-danger">Error checking status: ${error.message}</div>`);
        });
    }
});
