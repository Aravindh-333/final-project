document.addEventListener('DOMContentLoaded', function() {
    // Delete report functionality
    document.querySelectorAll('.report-delete').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const reportId = this.getAttribute('data-id');
            
            if (confirm('Are you sure you want to delete this report?')) {
                fetch(`/delete_report/${reportId}`, {
                    method: 'DELETE',
                    headers: {
                        'Content-Type': 'application/json',
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        this.closest('.report-card').style.opacity = '0';
                        setTimeout(() => {
                            this.closest('.report-card').remove();
                            
                            // If no reports left, show message
                            if (document.querySelectorAll('.report-card').length === 0) {
                                document.querySelector('.reports-grid').innerHTML = `
                                    <div class="no-reports">
                                        <p>No recognition reports found</p>
                                    </div>
                                `;
                            }
                        }, 300);
                    } else {
                        alert('Failed to delete report: ' + (data.error || 'Unknown error'));
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('Error deleting report');
                });
            }
        });
    });
});