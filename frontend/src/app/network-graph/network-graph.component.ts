import {
  Component,
  EventEmitter,
  Input,
  OnChanges,
  Output,
} from '@angular/core';
import * as d3 from 'd3';
import {
  D3DragEvent,
  Selection,
  Simulation,
  SimulationLinkDatum,
  SimulationNodeDatum,
} from 'd3';
import { ColorUtilities } from '../color-utilities';
import { Telegram } from '../telegram.interface';

export interface Node extends SimulationNodeDatum, Telegram {}

export interface Link extends SimulationLinkDatum<Node> {}

interface DragEvent extends D3DragEvent<SVGCircleElement, Node, Node> {}

@Component({
  selector: 'app-network-graph',
  templateUrl: './network-graph.component.html',
  styleUrls: ['./network-graph.component.scss'],
})
export class NetworkGraphComponent implements OnChanges {
  @Output() public selectionChange = new EventEmitter<number>();

  @Input() public nodes: Node[] = [];
  @Input() public links: Link[] = [];

  private svg?: Selection<SVGSVGElement, unknown, HTMLElement, any>;
  private g?: Selection<SVGGElement, unknown, HTMLElement, any>;

  private minZoom = 0.25;
  private maxZoom = 2.5;
  private panningMargin = 50;

  constructor() {}

  ngOnChanges() {
    this.generate();
  }

  generate() {
    this.clear();

    this.svg = d3
      .select('#network-graph')
      .append('svg')
      .attr('width', '100%')
      .attr('height', '100%')
      .attr('display', 'block');

    const rect = this.svg.node()!.getBoundingClientRect();
    const width = rect?.width;
    const height = rect?.height;

    this.g = this.svg.append('g');

    const simulation = d3
      .forceSimulation<Node>(this.nodes)
      .force(
        'link',
        d3.forceLink<Node, Link>(this.links).id((d) => d.id)
      )
      .force('charge', d3.forceManyBody().strength(-5))
      .force('center', d3.forceCenter(width / 2, height / 2));

    const link = this.g
      .append('g')
      .attr('stroke', '#999')
      .attr('stroke-opacity', 0.6)
      .selectAll('line')
      .data(this.links)
      .join('line')
      .attr('stroke-width', 1);

    const node = this.g
      .append('g')
      .attr('stroke', '#fff')
      .attr('stroke-width', 1.5)
      .selectAll('circle')
      .data(this.nodes)
      .join('circle')
      .style('fill', function (d) {
        return ColorUtilities.stringToColor(d.title);
      })
      .attr('r', 5)
      .on('click', this.click.bind(this))
      .call((simulation: any) => this.drag(simulation));

    node
      .append('title')
      .text(
        (telegram) =>
          `#${telegram.id} "${
            telegram.title
          }", ${telegram.date.toLocaleDateString()}`
      );

    simulation.on('tick', () => {
      this.setZoom();

      link
        .attr('x1', (d) => (d.source as Node).x!)
        .attr('y1', (d) => (d.source as Node).y!)
        .attr('x2', (d) => (d.target as Node).x!)
        .attr('y2', (d) => (d.target as Node).y!);

      node.attr('cx', (d) => d.x!).attr('cy', (d) => d.y!);
    });

    simulation.on('end', () => {
      this.setZoom();
    });
  }

  drag(simulation: Simulation<Node, Link>) {
    const dragStarted = (event: DragEvent) => {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      event.subject.fx = event.subject.x;
      event.subject.fy = event.subject.y;
    };

    const dragged = (event: DragEvent) => {
      event.subject.fx = event.x;
      event.subject.fy = event.y;
    };

    const dragEnded = (event: DragEvent) => {
      if (!event.active) simulation.alphaTarget(0);
      event.subject.fx = null;
      event.subject.fy = null;
    };

    return d3
      .drag<SVGCircleElement, Node>()
      .on('start', dragStarted)
      .on('drag', dragged)
      .on('end', dragEnded);
  }

  setZoom() {
    const boundingBox = this.g!.node()!.getBBox();

    const start: [number, number] = [
      boundingBox.x - this.panningMargin,
      boundingBox.y - this.panningMargin,
    ];
    const end: [number, number] = [
      boundingBox.x + boundingBox.width + this.panningMargin,
      boundingBox.y + boundingBox.height + this.panningMargin,
    ];

    const zoom = d3
      .zoom()
      .scaleExtent([this.minZoom, this.maxZoom])
      .translateExtent([start, end])
      .on('zoom', (event) => {
        this.g!.attr('transform', event.transform);
      });

    zoom(this.svg as unknown as Selection<Element, unknown, HTMLElement, any>);
  }

  clear() {
    this.svg?.remove();
  }

  click(_: unknown, node: Node) {
    this.selectionChange.emit(+node.id);
  }
}
