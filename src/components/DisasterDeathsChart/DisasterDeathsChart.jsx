import React from "react";
import './DisasterDeathsChart.css';
import {
    Chart as ChartJS,
    LineElement,
    CategoryScale,
    LinearScale,
    PointElement,
    Title,
    Tooltip,
    Legend
} from "chart.js";
import { Line } from "react-chartjs-2";

// Register Chart.js components
ChartJS.register(
    LineElement,
    CategoryScale,
    LinearScale,
    PointElement,
    Title,
    Tooltip,
    Legend
);

export default function DisasterDeathsChart() {
    const labels = [
        "2015", "2016", "2017", "2018", "2019", "2020",
        "2021", "2022", "2023", "2024", "2025", "2026",
        "2027", "2028", "2029", "2030"
    ];

    const data = {
        labels,
        datasets: [
            {
                label: "Actual Deaths (Historical)",
                data: [2500, 2800, 3000, 3300, 3500, 4000, 4200, 4600, 4800, 5000, null, null, null, null, null, null],
                borderColor: "red",
                backgroundColor: "rgba(255,0,0,0.2)",
                tension: 0.3,
                fill: false
            },
            {
                label: "Projected Deaths (with गरूड़ Copters)",
                data: [null, null, null, null, null, null, null, null, 4800, 4200, 3600, 3000, 2500, 2000, 1600, 1200],
                borderColor: "green",
                backgroundColor: "rgba(0,128,0,0.2)",
                tension: 0.3,
                borderDash: [6, 6], // dashed line for projection
                fill: false
            }
        ]
    };

    const options = {
        responsive: true,
        plugins: {
            title: {
                display: true,
                text: "Disaster Deaths in India vs. Projected Impact of गरूड़ Copters",
                font: { size: 18 }
            },
            legend: { position: "top" }
        },
        scales: {
            y: {
                beginAtZero: true,
                title: { display: true, text: "Number of Deaths" }
            },
            x: {
                title: { display: true, text: "Year" }
            }
        }
    };

    return (
        <div id="graph" style={{ width: "80%", margin: "auto", zIndex: 10}}>
            <Line data={data} options={options} />
        </div>
    );
}
