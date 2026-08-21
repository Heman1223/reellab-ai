import { useEffect, useRef, useState } from 'react';
import ForceGraph2D from 'react-force-graph-2d';

interface Node {
  id: string;
  wave: number;
  val: number;
  color: string;
}

interface Link {
  source: string;
  target: string;
}

interface GraphData {
  nodes: Node[];
  links: Link[];
}

export function PropagationGraph({ waves }: { waves: any[] }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 600, height: 500 });
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] });
  const [activeNode, setActiveNode] = useState<any>(null);

  useEffect(() => {
    // Generate a visual pseudo-graph based on the waves data
    const nodes: Node[] = [];
    const links: Link[] = [];

    // Central Node (The Reel)
    nodes.push({ id: 'reel', wave: -1, val: 5, color: '#0f172a' }); // Dark center

    let currentId = 0;
    let prevWaveNodes: string[] = ['reel'];

    const colors = ['#2563eb', '#94a3b8', '#ea580c']; // Blue, grey, orange

    waves.forEach((waveData, waveIndex) => {
      // Scale down nodes for visualization
      const visualNodeCount = Math.min(Math.max(Math.floor(waveData.reach / 10), 5), 50);
      const currentWaveNodes: string[] = [];
      const waveColor = colors[waveIndex % colors.length];

      for (let i = 0; i < visualNodeCount; i++) {
        const nodeId = `n_${currentId++}`;
        nodes.push({ id: nodeId, wave: waveIndex, val: 2, color: waveColor });
        currentWaveNodes.push(nodeId);

        // Connect to a random node from the previous wave
        const sourceNode = prevWaveNodes[Math.floor(Math.random() * prevWaveNodes.length)];
        links.push({ source: sourceNode, target: nodeId });
      }
      
      prevWaveNodes = currentWaveNodes;
    });

    setGraphData({ nodes, links });
  }, [waves]);

  useEffect(() => {
    if (containerRef.current) {
      setDimensions({
        width: containerRef.current.clientWidth,
        height: 500
      });
    }
  }, []);

  return (
    <div ref={containerRef} className="w-full h-[500px] border border-ink-700 bg-ink-800 rounded-xl overflow-hidden relative shadow-sm">
      <ForceGraph2D
        width={dimensions.width}
        height={dimensions.height}
        graphData={graphData}
        nodeColor={(node: any) => node.color}
        nodeRelSize={4}
        linkColor={() => '#cbd5e1'}
        d3AlphaDecay={0.05}
        d3VelocityDecay={0.4}
        onNodeClick={(node) => setActiveNode(node)}
        onBackgroundClick={() => setActiveNode(null)}
      />

      {activeNode && (
        <div className="absolute top-4 right-4 w-72 bg-ink-800 border border-ink-700 rounded-lg p-4 shadow-xl text-sm transition-all animate-in fade-in slide-in-from-right-4 z-10">
          <div className="flex justify-between items-start mb-2">
            <h4 className="font-bold text-slate-900 text-base font-serif">
              {activeNode.id === 'reel' ? 'The Content (Seed)' : `Persona ${activeNode.id}`}
            </h4>
            <button onClick={() => setActiveNode(null)} className="text-slate-400 hover:text-slate-600">
              ✕
            </button>
          </div>
          
          {activeNode.id !== 'reel' ? (
            <>
              <p className="text-slate-500 mb-4 pb-4 border-b border-ink-700 text-xs">
                25 • Female • Sub-niche Viewer<br/>
                Follows tech, fitness, and lifestyle.
              </p>
              
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-slate-400 uppercase text-[10px] font-bold tracking-wider">Action</span>
                  <span className="font-semibold text-accent text-[10px] px-1.5 py-0.5 border border-accent/20 rounded">SHARED</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-400 uppercase text-[10px] font-bold tracking-wider">Confidence</span>
                  <div className="w-24 h-1.5 bg-ink-700 rounded-full overflow-hidden">
                    <div className="bg-accent h-full w-[85%]"></div>
                  </div>
                </div>
              </div>
              
              <div className="mt-4 pt-4 border-t border-ink-700">
                <span className="text-slate-400 uppercase text-[10px] font-bold block mb-1 tracking-wider">Reasoning</span>
                <p className="text-slate-600 text-xs leading-relaxed italic">
                  "This perfectly describes the issue I face every day. I forwarded it immediately to my accountability group chat."
                </p>
              </div>
            </>
          ) : (
            <p className="text-slate-500 text-xs">Central node representing the Reel.</p>
          )}
        </div>
      )}
    </div>
  );
}
