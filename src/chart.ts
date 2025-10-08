// Chart.js wrapper with instance management

import { Chart as ChartT, ChartConfiguration, ChartType } from "chart.js";
import Chart from "https://esm.sh/chart.js@4.4.0/auto";

import { ChartData, TrendsData } from "./types";

export class ChartService {
  private charts: Map<string, Chart> = new Map();

  /**
   * Create or update a line chart
   */
  createLineChart(
    canvasId: string,
    data: TrendsData,
    title: string = "Line Chart"
  ): ChartT | null {
    const canvas = document.getElementById(canvasId) as HTMLCanvasElement;
    if (!canvas) {
      console.error(`Canvas with id ${canvasId} not found`);
      return null;
    }

    // Destroy existing chart if it exists
    this.destroyChart(canvasId);

    const ctx = canvas.getContext("2d");
    if (!ctx) return null;

    const datasets: any[] = [
      {
        label: "Publications",
        data: data.publications,
        borderColor: "#3182ce",
        backgroundColor: "rgba(49, 130, 206, 0.1)",
        tension: 0.3,
        fill: true,
      },
    ];

    if (data.citations) {
      datasets.push({
        label: "Avg Citations",
        data: data.citations,
        borderColor: "#38a169",
        backgroundColor: "rgba(56, 161, 105, 0.1)",
        tension: 0.3,
        fill: true,
      });
    }

    const config: ChartConfiguration = {
      type: "line",
      data: {
        labels: data.labels,
        datasets,
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: "top" },
          title: { display: true, text: title },
        },
      },
    };

    const chart = new Chart(ctx, config);
    this.charts.set(canvasId, chart);
    return chart;
  }

  /**
   * Create or update a bar chart
   */
  createBarChart(
    canvasId: string,
    data: ChartData,
    title: string = "Bar Chart",
    options: { horizontal?: boolean; color?: string } = {}
  ): ChartT | null {
    const canvas = document.getElementById(canvasId) as HTMLCanvasElement;
    if (!canvas) {
      console.error(`Canvas with id ${canvasId} not found`);
      return null;
    }

    this.destroyChart(canvasId);

    const ctx = canvas.getContext("2d");
    if (!ctx) return null;

    const config: ChartConfiguration = {
      type: "bar",
      data: {
        labels: data.labels,
        datasets: [
          {
            label: "Count",
            data: data.data,
            backgroundColor: options.color || "#3182ce",
            borderRadius: 5,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: options.horizontal ? "y" : "x",
        plugins: {
          legend: { display: false },
          title: { display: true, text: title },
        },
        scales: {
          x: options.horizontal
            ? { beginAtZero: true }
            : {
                ticks: { maxRotation: 45, minRotation: 45 },
              },
          y: options.horizontal ? {} : { beginAtZero: true },
        },
      },
    };

    const chart = new Chart(ctx, config);
    this.charts.set(canvasId, chart);
    return chart;
  }

  /**
   * Create or update a doughnut chart
   */
  createDoughnutChart(
    canvasId: string,
    data: ChartData,
    title: string = "Doughnut Chart",
    colors?: string[]
  ): ChartT | null {
    const canvas = document.getElementById(canvasId) as HTMLCanvasElement;
    if (!canvas) {
      console.error(`Canvas with id ${canvasId} not found`);
      return null;
    }

    this.destroyChart(canvasId);

    const ctx = canvas.getContext("2d");
    if (!ctx) return null;

    const defaultColors = [
      "#3182ce",
      "#38a169",
      "#d69e2e",
      "#e53e3e",
      "#805ad5",
      "#dd6b20",
      "#319795",
      "#d53f8c",
      "#4299e1",
      "#48bb78",
    ];

    const config: ChartConfiguration = {
      type: "doughnut",
      data: {
        labels: data.labels,
        datasets: [
          {
            data: data.data,
            backgroundColor: colors || defaultColors,
            borderWidth: 0,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: "right" },
          title: { display: true, text: title },
        },
      },
    };

    const chart = new Chart(ctx, config);
    this.charts.set(canvasId, chart);
    return chart;
  }

  /**
   * Destroy a specific chart
   */
  destroyChart(canvasId: string): void {
    const chart = this.charts.get(canvasId);
    if (chart) {
      chart.destroy();
      this.charts.delete(canvasId);
    }
  }

  /**
   * Destroy all charts
   */
  destroyAllCharts(): void {
    this.charts.forEach((chart) => chart.destroy());
    this.charts.clear();
  }

  /**
   * Get a chart instance
   */
  getChart(canvasId: string): ChartT | undefined {
    return this.charts.get(canvasId);
  }

  /**
   * Update chart data
   */
  updateChartData(canvasId: string, newData: any): boolean {
    const chart = this.charts.get(canvasId);
    if (chart) {
      chart.data = newData;
      chart.update();
      return true;
    }
    return false;
  }
}
