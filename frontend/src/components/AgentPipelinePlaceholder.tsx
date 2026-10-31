import { Bot, ArrowRight } from 'lucide-react'

const AGENTS = ['Triage', 'Coverage', 'Fraud', 'Decision'] as const

export function AgentPipelinePlaceholder() {
  return (
    <div className="rounded-lg border border-dashed border-purple-300 bg-purple-50 p-6">
      <div className="mb-4 flex items-center gap-2 text-purple-700">
        <Bot className="h-5 w-5" />
        <span className="font-semibold">Agent Pipeline</span>
        <span className="rounded-full bg-purple-200 px-2 py-0.5 text-xs">Coming in Step 6</span>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {AGENTS.map((agent, i) => (
          <div key={agent} className="flex items-center gap-2">
            <div className="rounded-md border border-purple-200 bg-white px-3 py-2 text-sm text-purple-800 shadow-sm">
              <span className="text-xs text-purple-400 block">{i + 1}</span>
              {agent} Agent
            </div>
            {i < AGENTS.length - 1 && <ArrowRight className="h-4 w-4 text-purple-300" />}
          </div>
        ))}
      </div>

      <p className="mt-4 text-xs text-purple-500">
        Four-agent pipeline will run deterministic pre-checks, then invoke Triage → Coverage → Fraud → Decision
        agents via OpenAI Agents SDK + Bedrock. Output will appear here.
      </p>
    </div>
  )
}
