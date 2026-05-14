// Admin Dashboard Charts
document.addEventListener('DOMContentLoaded', function() {
    // Chart.js configuration
    Chart.defaults.font.family = "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif";
    Chart.defaults.color = '#666';
    
    // Get data from the page
    const chartData = window.adminChartData || {};
    console.log('Admin chart data:', chartData);
    
    // Donation Status Pie Chart
    const donationStatusCtx = document.getElementById('donationStatusChart');
    if (donationStatusCtx) {
        new Chart(donationStatusCtx.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: ['Available', 'Claimed', 'Shipped', 'Unavailable'],
                datasets: [{
                    data: [
                        chartData.available_donations || 0,
                        chartData.claimed_donations || 0,
                        chartData.shipped_donations || 0,
                        chartData.unavailable_donations || 0
                    ],
                    backgroundColor: [
                        '#28a745',  // Available - Green
                        '#ffc107',  // Claimed - Yellow
                        '#17a2b8',  // Shipped - Blue
                        '#dc3545'   // Unavailable - Red
                    ],
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 20,
                            usePointStyle: true
                        }
                    }
                }
            }
        });
    }
    
    // User Activity Chart
    const userActivityCtx = document.getElementById('userActivityChart');
    if (userActivityCtx) {
        new Chart(userActivityCtx.getContext('2d'), {
            type: 'line',
            data: {
                labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
                datasets: [{
                    label: 'New Users',
                    data: [2, 4, 6, chartData.new_users_period || 0],
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    tension: 0.4,
                    fill: true
                }, {
                    label: 'New Donations',
                    data: [3, 5, 7, chartData.new_donations_period || 0],
                    borderColor: '#28a745',
                    backgroundColor: 'rgba(40, 167, 69, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0,0,0,0.1)'
                        }
                    },
                    x: {
                        grid: {
                            color: 'rgba(0,0,0,0.1)'
                        }
                    }
                },
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 20,
                            usePointStyle: true
                        }
                    }
                }
            }
        });
    }
    
    // Donations by Category Chart
    const categoryCtx = document.getElementById('categoryChart');
    if (categoryCtx && chartData.category_stats) {
        const categoryData = chartData.category_stats;
        console.log('Category data for chart:', categoryData);
        
        new Chart(categoryCtx.getContext('2d'), {
            type: 'bar',
            data: {
                labels: categoryData.map(item => item.item__category || 'Unknown'),
                datasets: [{
                    label: 'Available',
                    data: categoryData.map(item => item.available_count || 0),
                    backgroundColor: '#28a745',
                    borderColor: '#28a745',
                    borderWidth: 1
                }, {
                    label: 'Claimed',
                    data: categoryData.map(item => item.claimed_count || 0),
                    backgroundColor: '#ffc107',
                    borderColor: '#ffc107',
                    borderWidth: 1
                }, {
                    label: 'Shipped',
                    data: categoryData.map(item => item.shipped_count || 0),
                    backgroundColor: '#17a2b8',
                    borderColor: '#17a2b8',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        stacked: false,
                        grid: {
                            color: 'rgba(0,0,0,0.1)'
                        }
                    },
                    x: {
                        grid: {
                            color: 'rgba(0,0,0,0.1)'
                        }
                    }
                },
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 20,
                            usePointStyle: true
                        }
                    }
                }
            }
        });
    }
    
    // Monthly Trends Chart
    const monthlyTrendsCtx = document.getElementById('monthlyTrendsChart');
    if (monthlyTrendsCtx) {
        new Chart(monthlyTrendsCtx.getContext('2d'), {
            type: 'line',
            data: {
                labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                datasets: [{
                    label: 'Donations',
                    data: [5, 8, 12, 15, 18, chartData.total_donations || 0],
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    tension: 0.4,
                    fill: true
                }, {
                    label: 'Users',
                    data: [3, 6, 9, 12, 15, chartData.total_users || 0],
                    borderColor: '#28a745',
                    backgroundColor: 'rgba(40, 167, 69, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0,0,0,0.1)'
                        }
                    },
                    x: {
                        grid: {
                            color: 'rgba(0,0,0,0.1)'
                        }
                    }
                },
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 20,
                            usePointStyle: true
                        }
                    }
                }
            }
        });
    }
    
    // Volunteer Activity Status Pie Chart
    const volunteerActivityStatusCtx = document.getElementById('volunteerActivityStatusChart');
    if (volunteerActivityStatusCtx && chartData.volunteer_activity_status) {
        const statusData = chartData.volunteer_activity_status;
        new Chart(volunteerActivityStatusCtx.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: ['Joined', 'Completed', 'Cancelled'],
                datasets: [{
                    data: [
                        statusData.available || 0,  // This is actually joined activities
                        statusData.completed || 0,
                        statusData.cancelled || 0
                    ],
                    backgroundColor: [
                        '#ffc107',  // Joined - Yellow
                        '#17a2b8',  // Completed - Blue
                        '#dc3545'   // Cancelled - Red
                    ],
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 20,
                            usePointStyle: true
                        }
                    }
                }
            }
        });
    }
    
    // Volunteer Activity Trends Line Chart
    const volunteerActivityTrendsCtx = document.getElementById('volunteerActivityTrendsChart');
    if (volunteerActivityTrendsCtx && chartData.volunteer_activity_trends) {
        const trendsData = chartData.volunteer_activity_trends;
        const labels = trendsData.map(item => item.date);
        const createdData = trendsData.map(item => item.activities_created || 0);
        const completedData = trendsData.map(item => item.activities_completed || 0);
        
        new Chart(volunteerActivityTrendsCtx.getContext('2d'), {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Activities Created',
                    data: createdData,
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    tension: 0.4,
                    fill: true
                }, {
                    label: 'Activities Completed',
                    data: completedData,
                    borderColor: '#28a745',
                    backgroundColor: 'rgba(40, 167, 69, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        },
                        grid: {
                            color: 'rgba(0,0,0,0.1)'
                        }
                    },
                    x: {
                        grid: {
                            color: 'rgba(0,0,0,0.1)'
                        }
                    }
                },
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 20,
                            usePointStyle: true
                        }
                    }
                }
            }
        });
    }
});
