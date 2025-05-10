document.addEventListener('DOMContentLoaded', function() {
    // Flash message auto-dismiss
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(message => {
        setTimeout(() => {
            message.style.opacity = '0';
            setTimeout(() => {
                message.remove();
            }, 500);
        }, 5000);
    });

    // Form validation for post creation
    const postForm = document.querySelector('.post-form');
    if (postForm) {
        postForm.addEventListener('submit', function(event) {
            const contentField = this.querySelector('textarea[name="content"]');
            if (!contentField.value.trim()) {
                event.preventDefault();
                alert("Post cannot be empty!");
            }
        });

        // Character counter for post textarea
        const textarea = postForm.querySelector('textarea');
        const maxLength = textarea.getAttribute('maxlength');
        
        // Create and append character counter
        const charCounter = document.createElement('div');
        charCounter.classList.add('char-counter');
        charCounter.textContent = `0/${maxLength}`;
        textarea.parentNode.appendChild(charCounter);
        
        // Update character counter on input
        textarea.addEventListener('input', function() {
            const currentLength = this.value.length;
            charCounter.textContent = `${currentLength}/${maxLength}`;
            
            if (currentLength > maxLength * 0.8) {
                charCounter.classList.add('warning');
            } else {
                charCounter.classList.remove('warning');
            }
        });
    }

    // Check for posts that need to be refreshed with server time
    function refreshPostTimers() {
        const posts = document.querySelectorAll('.post');
        const now = new Date();
        
        posts.forEach(post => {
            const postId = post.dataset.postId;
            const remainingSeconds = parseFloat(post.dataset.remainingSeconds);
            
            // If remaining time is low or timestamp is old, refresh from server
            if (remainingSeconds < 60) {
                fetch(`/api/post/${postId}/remaining`)
                    .then(response => response.json())
                    .then(data => {
                        post.dataset.remainingSeconds = data.remaining_seconds;
                        
                        // If post should be gone already, remove it
                        if (data.remaining_seconds <= 0) {
                            post.classList.add('vanishing');
                            setTimeout(() => {
                                post.remove();
                            }, 1000);
                        }
                    })
                    .catch(error => console.error('Error refreshing post timer:', error));
            }
        });
    }
    
    // Refresh post timers every minute
    setInterval(refreshPostTimers, 60000);
});