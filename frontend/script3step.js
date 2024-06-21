$(document).ready(function() {
    // Bootstrap form validation
    const form = document.getElementById('recommendation-form');

    form.addEventListener('submit', function(event) {
        event.preventDefault(); // Prevents the form from submitting traditionally
        event.stopPropagation(); // Stops the event from bubbling up the DOM tree

        if (form.checkValidity()) {
            requestRecommendations(); // If form is valid, proceed to request recommendations
        }

        form.classList.add('was-validated'); // Adds Bootstrap's 'was-validated' class for styling
    }, false);

    function requestRecommendations() {
        const country = $('#country').val(); // Retrieves value of country input using jQuery
        const season = $('#season').val();   // Retrieves value of season input using jQuery
        const statusDiv = $('#status');      // Retrieves status div using jQuery
        const recommendationsDiv = $('#recommendations'); // Retrieves recommendations div using jQuery

        // Update statusDiv to show that recommendations are being requested
        statusDiv.html('<div class="alert alert-info">Requesting recommendations...</div>');
        recommendationsDiv.html(''); // Clear recommendations div

        // Make a POST request to server to fetch recommendations
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
            const uid = data.uid; // Extract unique ID from response data
            checkStatus(uid);     // Call checkStatus function with the UID
        })
        .catch(error => {
            statusDiv.html(`<div class="alert alert-danger">Error: ${error.message}</div>`); // Display error message if fetch fails
        });
    }

    function checkStatus(uid) {
        const statusDiv = $('#status');             // Retrieves status div using jQuery
        const recommendationsDiv = $('#recommendations'); // Retrieves recommendations div using jQuery

        // Fetch status of recommendations based on UID
        fetch(`http://localhost:3000/recommendations/${uid}/status`)
        .then(response => response.json()) // Parse response as JSON
        .then(data => {
            // Handle different statuses returned from server
            if (data.status === 'pending') {
                statusDiv.html('<div class="alert alert-info">Recommendations are being processed. Please wait...</div>');
                setTimeout(() => checkStatus(uid), 2000); // Poll status again after 2 seconds if pending
            } else if (data.status === 'completed') {
                statusDiv.html('<div class="alert alert-success">Recommendations received:</div>');
                // Fetch recommendation data once status is completed
                fetchRecommendationData(uid);
            } else if (data.status === 'error') {
                statusDiv.html(`<div class="alert alert-danger">Error: ${data.message}</div>`);
            } else {
                statusDiv.html(`<div class="alert alert-warning">Unknown status: ${data.status}</div>`);
            }
        })
        .catch(error => {
            statusDiv.html(`<div class="alert alert-danger">Error checking status: ${error.message}</div>`); // Display error if status check fails
        });
    }

    function fetchRecommendationData(uid) {
        const statusDiv = $('#status');             // Retrieves status div using jQuery
        const recommendationsDiv = $('#recommendations'); // Retrieves recommendations div using jQuery

        // Fetch recommendation data based on UID
        fetch(`http://localhost:3000/recommendations/${uid}`)
        .then(response => response.json()) // Parse response as JSON
        .then(data => {
            // Display recommendations in recommendationsDiv
            recommendationsDiv.html(data.recommendations.map(rec => `<div class="recommendation alert alert-light">${rec}</div>`).join(''));
        })
        .catch(error => {
            statusDiv.html(`<div class="alert alert-danger">Error fetching recommendations: ${error.message}</div>`); // Display error if fetching recommendation data fails
        });
    }
});
