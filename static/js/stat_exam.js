document.addEventListener("DOMContentLoaded", function () {
    const timeElement = document.getElementById("time-remaining");
    const resultsSection = document.getElementById("results");
    const totalPointsElement = document.getElementById("total-points");
    const detailedResultsElement = document.getElementById("detailed-results");
    const form = document.getElementById("exam-form");
    const submitButton = document.querySelector(".submit-button");

    let remainingTime = 15 * 60; // 15 minutes in seconds

    // Update Timer
    function updateTimer() {
        const minutes = Math.floor(remainingTime / 60);
        const seconds = remainingTime % 60;
        timeElement.textContent = `${minutes}:${seconds.toString().padStart(2, "0")}`;

        if (remainingTime <= 0) {
            clearInterval(timer);
            submitButton.disabled = true;
            alert("Time's up! Your answers will now be submitted.");
            submitExam(); // Auto-submit on timer expiry
        }
        remainingTime--;
    }

    const timer = setInterval(updateTimer, 1000);

    // Submit Exam
    function submitExam() {
        const formData = new FormData(form);
        const answers = {};
    
        // Collect answers from form data
        for (let [key, value] of formData.entries()) {
            answers[key] = value;
        }

        // Add course_code to the URL
        // Extract course_code from the hidden input field
        const courseCode = formData.get("course_code");
        const submitUrl = `/submit_stat_exam/${courseCode}`;
    
        // Check if all questions are answered
        const totalQuestions = form.querySelectorAll(".question").length;
        if (Object.keys(answers).length < totalQuestions) {
            alert("Please answer all questions before submitting.");
            return;
        }
        
        fetch(submitUrl, {
            method: "POST",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded", // Use form data encoding
            },
            body: new URLSearchParams(answers), // This will send data as form URL encoded
        })
            .then((response) => response.json())
            .then((data) => {
                if (data.total_points !== undefined) {
                    // Display results
                    resultsSection.classList.remove("hidden");
                    totalPointsElement.textContent = data.total_points;
                    detailedResultsElement.innerHTML = data.results_html;
    
                    // Disable the form to prevent further submissions
                    form.style.display = "none";
                    submitButton.disabled = true;
                } else {
                    alert("There was an error processing your results. Please try again.");
                }
            })
            .catch((error) => {
                console.error("Error submitting exam:", error);
                alert("An error occurred while submitting your exam. Please try again.");
            });
    }
    

    // Bind Submit Button Click
    submitButton.addEventListener("click", function () {
        clearInterval(timer);
        submitExam();
    });
});
