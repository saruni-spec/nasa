// Knowledge graph visualization

import { APIService } from "./api";
import { ToastService } from "./toast";
import { KnowledgeGraphData, GraphNode } from "./types";

// Declare d3 as global
declare const d3: any;

export class KnowledgeGraphController {
  private apiService: APIService;
  private toastService: ToastService;
  private graphData: KnowledgeGraphData | null = null;
  private simulation: any = null;

  constructor(apiService: APIService, toastService: ToastService) {
    this.apiService = apiService;
    this.toastService = toastService;
  }

  /**
   * Initialize knowledge graph
   */
  initialize(): void {
    console.log("Knowledge graph controller initialized");
  }

  /**
   * Load and display knowledge graph
   */
  async loadGraph(): Promise<void> {
    try {
      this.toastService.info("Loading knowledge graph...");

      const graphData = await this.apiService.getKnowledgeGraph(50);
      this.graphData = graphData;

      this.displayGraph(graphData);

      this.toastService.success("Knowledge graph loaded successfully");
    } catch (error) {
      console.error("Error loading knowledge graph:", error);
      this.toastService.error("Failed to load knowledge graph");
    }
  }

  /**
   * Display the knowledge graph
   */
  private displayGraph(data: KnowledgeGraphData): void {
    const graphContainer = document.querySelector(
      "#knowledge-graph-tab .card-content > div:first-child"
    ) as HTMLElement;

    if (!graphContainer) {
      console.error("Graph container not found");
      return;
    }

    // Clear existing content
    graphContainer.innerHTML = "";
    graphContainer.style.height = "500px";
    graphContainer.style.background = "white";
    graphContainer.style.position = "relative";

    // Add SVG element
    const svg = d3
      .select(graphContainer)
      .append("svg")
      .attr("width", "100%")
      .attr("height", "500px")
      .style("border-radius", "8px")
      .style("border", "1px solid var(--border)");

    const width = graphContainer.offsetWidth;
    const height = 500;

    // Create zoom behavior
    const g = svg.append("g");
    const zoom = d3
      .zoom()
      .scaleExtent([0.5, 3])
      .on("zoom", (event: any) => {
        g.attr("transform", event.transform);
      });
    svg.call(zoom);

    // Color scale for different node types
    const colorScale: { [key: string]: string } = {
      biological_system: "#3182ce",
      experiment_type: "#38a169",
      organism: "#d69e2e",
      default: "#805ad5",
    };

    // Create force simulation
    this.simulation = d3
      .forceSimulation(data.nodes)
      .force(
        "link",
        d3
          .forceLink(data.edges)
          .id((d: any) => d.id)
          .distance(100)
      )
      .force("charge", d3.forceManyBody().strength(-400))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force(
        "collision",
        d3.forceCollide().radius((d: any) => (d.size || 5) * 3)
      );

    // Create links
    const link = g
      .append("g")
      .selectAll("line")
      .data(data.edges)
      .join("line")
      .attr("stroke", "#cbd5e0")
      .attr("stroke-opacity", 0.6)
      .attr("stroke-width", (d: any) => Math.sqrt(d.weight || 1) * 0.8);

    // Create nodes
    const node = g
      .append("g")
      .selectAll("circle")
      .data(data.nodes)
      .join("circle")
      .attr("r", (d: any) => (d.size || 5) * 2.5)
      .attr("fill", (d: any) => colorScale[d.type] || colorScale.default)
      .attr("stroke", "#fff")
      .attr("stroke-width", 2)
      .style("cursor", "pointer")
      .call(this.createDragBehavior())
      .on("mouseover", this.handleNodeMouseOver.bind(this))
      .on("mouseout", this.handleNodeMouseOut.bind(this));

    // Create labels
    const label = g
      .append("g")
      .selectAll("text")
      .data(data.nodes)
      .join("text")
      .attr("text-anchor", "middle")
      .attr("dy", ".35em")
      .attr("font-size", "11px")
      .attr("font-weight", "500")
      .attr("pointer-events", "none")
      .style(
        "text-shadow",
        "0 1px 2px white, 1px 0 2px white, -1px 0 2px white, 0 -1px 2px white"
      )
      .text((d: any) => d.label);

    // Update positions on tick
    this.simulation.on("tick", () => {
      link
        .attr("x1", (d: any) => d.source.x)
        .attr("y1", (d: any) => d.source.y)
        .attr("x2", (d: any) => d.target.x)
        .attr("y2", (d: any) => d.target.y);

      node.attr("cx", (d: any) => d.x).attr("cy", (d: any) => d.y);

      label.attr("x", (d: any) => d.x).attr("y", (d: any) => d.y);
    });

    // Add controls and stats
    this.addControls(graphContainer, svg, zoom);
    this.addStats(graphContainer, data);
  }

  /**
   * Create drag behavior
   */
  private createDragBehavior(): any {
    return d3
      .drag()
      .on("start", (event: any) => {
        if (!event.active) this.simulation.alphaTarget(0.3).restart();
        event.subject.fx = event.subject.x;
        event.subject.fy = event.subject.y;
      })
      .on("drag", (event: any) => {
        event.subject.fx = event.x;
        event.subject.fy = event.y;
      })
      .on("end", (event: any) => {
        if (!event.active) this.simulation.alphaTarget(0);
        event.subject.fx = null;
        event.subject.fy = null;
      });
  }

  /**
   * Handle node mouse over
   */
  private handleNodeMouseOver(event: any, d: GraphNode): void {
    d3.select(event.currentTarget)
      .transition()
      .duration(200)
      .attr("r", (d.size || 5) * 3.5)
      .attr("stroke", "#3182ce")
      .attr("stroke-width", 3);

    // Show tooltip
    const tooltip = document.createElement("div");
    tooltip.id = "graph-tooltip";
    tooltip.style.cssText = `
            position: absolute;
            background: rgba(0, 0, 0, 0.85);
            color: white;
            padding: 10px;
            border-radius: 6px;
            font-size: 13px;
            pointer-events: none;
            z-index: 1000;
            max-width: 200px;
        `;
    tooltip.innerHTML = `<strong>${d.label}</strong><br>Connections: ${
      d.size || "N/A"
    }`;
    tooltip.style.left = event.pageX + 10 + "px";
    tooltip.style.top = event.pageY - 10 + "px";
    document.body.appendChild(tooltip);
  }

  /**
   * Handle node mouse out
   */
  private handleNodeMouseOut(event: any, d: GraphNode): void {
    d3.select(event.currentTarget)
      .transition()
      .duration(200)
      .attr("r", (d.size || 5) * 2.5)
      .attr("stroke", "#fff")
      .attr("stroke-width", 2);

    const tooltip = document.getElementById("graph-tooltip");
    if (tooltip) tooltip.remove();
  }

  /**
   * Add controls overlay
   */
  private addControls(container: HTMLElement, svg: any, zoom: any): void {
    const controls = document.createElement("div");
    controls.style.cssText = `
            position: absolute;
            top: 15px;
            right: 15px;
            background: rgba(255, 255, 255, 0.95);
            padding: 12px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
            z-index: 10;
        `;

    const resetBtn = this.createControlButton("Reset View", () => {
      svg.transition().duration(750).call(zoom.transform, d3.zoomIdentity);
    });

    const toggleBtn = this.createControlButton("Toggle Labels", () => {
      const labels = svg.selectAll("text");
      const currentOpacity = labels.style("opacity");
      labels.style("opacity", currentOpacity === "0" ? 1 : 0);
    });

    controls.appendChild(resetBtn);
    controls.appendChild(toggleBtn);
    container.appendChild(controls);
  }

  /**
   * Create control button
   */
  private createControlButton(
    text: string,
    onClick: () => void
  ): HTMLButtonElement {
    const button = document.createElement("button");
    button.textContent = text;
    button.style.cssText = `
            display: block;
            width: 100%;
            padding: 8px 12px;
            background: var(--accent);
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 0.9rem;
            margin-bottom: 8px;
        `;
    button.onclick = onClick;
    return button;
  }

  /**
   * Add stats overlay
   */
  private addStats(container: HTMLElement, data: KnowledgeGraphData): void {
    const stats = document.createElement("div");
    stats.style.cssText = `
            position: absolute;
            bottom: 15px;
            left: 15px;
            background: rgba(255, 255, 255, 0.95);
            padding: 12px 15px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
            font-size: 0.85rem;
            color: var(--text-light);
        `;
    stats.innerHTML = `
            <strong style="color: var(--primary);">Graph Stats:</strong><br>
            Concepts: ${data.nodes.length} | Relationships: ${data.edges.length}
        `;
    container.appendChild(stats);
  }

  /**
   * Cleanup
   */
  destroy(): void {
    if (this.simulation) {
      this.simulation.stop();
    }
    const tooltip = document.getElementById("graph-tooltip");
    if (tooltip) tooltip.remove();
  }
}
