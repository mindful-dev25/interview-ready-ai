import AnalysisProgress from "@/components/AnalysisProgress";
import EvidencePanel from "@/components/EvidencePanel";
import FinalReport from "@/components/FinalReport";
import GuardrailBadge from "@/components/GuardrailBadge";
import HumanReviewControls from "@/components/HumanReviewControls";
import InterviewQuestionCard from "@/components/InterviewQuestionCard";
import JobUrlInput from "@/components/JobUrlInput";
import ResumeUpload from "@/components/ResumeUpload";

const sampleEvidence = [
  {
    source: "Resume",
    quote: "Led cross-functional AI prototype delivery.",
    relevance: "Supports leadership and delivery examples.",
  },
  {
    source: "Job Description",
    quote: "Experience with RAG systems and production APIs.",
    relevance: "Maps directly to target role requirements.",
  },
];

export default function Home() {
  return (
    <main className="min-h-screen px-6 py-8 md:px-10">
      <div className="mx-auto flex max-w-6xl flex-col gap-8">
        <header className="flex flex-col gap-3">
          <p className="text-sm font-medium text-primary">Local LLM interview prep</p>
          <h1 className="max-w-3xl text-4xl font-semibold tracking-normal text-foreground md:text-5xl">
            Interview Ready AI
          </h1>
          <p className="max-w-2xl text-base leading-7 text-muted-foreground">
            Upload resume context, add a job URL, review grounded answer drafts, and keep humans in control before the final report.
          </p>
        </header>

        <section className="grid gap-4 md:grid-cols-[1fr_1fr]">
          <ResumeUpload />
          <JobUrlInput />
        </section>

        <AnalysisProgress status="Queued" />

        <section className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
          <InterviewQuestionCard
            question="Tell me about a project where you used AI to solve a practical problem."
            answer="TODO: Generate a tailored, evidence-backed answer after the agent workflow is implemented."
          >
            <GuardrailBadge label="Needs evidence review" tone="warning" />
          </InterviewQuestionCard>
          <EvidencePanel items={sampleEvidence} />
        </section>

        <HumanReviewControls />
        <FinalReport />
      </div>
    </main>
  );
}
