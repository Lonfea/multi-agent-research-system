from dataclasses import dataclass

from crewai import Agent, Crew, Process, Task
from crewai_tools import SerperApiTool

from app.models import FactCheckReport, SupervisorDecision


@dataclass(frozen=True)
class ResearchOutcome:
    report: str
    fact_check: FactCheckReport
    supervisor: SupervisorDecision
    consensus_approved: bool
    task_outputs: list[str]


class ResearchPipeline:
    def __init__(
        self,
        research_model: str,
        supervisor_model: str,
        fact_check_threshold: float,
    ):
        self.research_model = research_model
        self.supervisor_model = supervisor_model
        self.fact_check_threshold = fact_check_threshold

    def build_crew(self, topic: str) -> Crew:
        search = SerperApiTool()

        researcher = Agent(
            role="Researcher",
            goal="Find primary, recent, and diverse evidence relevant to the research question.",
            backstory=(
                "You are a rigorous researcher. Prefer primary sources, record URLs and dates, "
                "and separate evidence from interpretation."
            ),
            tools=[search],
            llm=self.research_model,
            verbose=False,
        )
        writer = Agent(
            role="Writer",
            goal="Turn verified research into a clear report without overstating evidence.",
            backstory="You write concise research reports and preserve source attribution.",
            llm=self.research_model,
            verbose=False,
        )
        fact_checker = Agent(
            role="Fact Checker",
            goal="Challenge factual claims and identify unsupported or contradictory statements.",
            backstory=(
                "You are adversarial about factual accuracy. Check claims against the research "
                "packet and flag weak evidence instead of guessing."
            ),
            tools=[search],
            llm=self.research_model,
            verbose=False,
        )
        supervisor = Agent(
            role="Research Supervisor",
            goal="Coordinate specialists and approve only reports supported by strong evidence.",
            backstory=(
                "You manage a research team. You value traceability, uncertainty disclosure, "
                "and explicit revision instructions."
            ),
            allow_delegation=True,
            llm=self.supervisor_model,
            verbose=False,
        )

        research_task = Task(
            description=(
                f"Research this topic: {topic}\n"
                "Return a source packet with key findings, URLs, publication dates, and notes "
                "on source quality. Prefer primary and recent sources."
            ),
            expected_output="A structured evidence packet with sources and key findings.",
            agent=researcher,
        )

        draft_task = Task(
            description=(
                "Write a concise research report using the evidence packet. Distinguish facts, "
                "inference, and uncertainty. Include source links for material claims."
            ),
            expected_output="A sourced research report in Markdown.",
            agent=writer,
            context=[research_task],
        )

        fact_task = Task(
            description=(
                "Audit the draft claim by claim. Verify material claims against the evidence "
                "packet and independent searches where useful. Score overall verification from 0 to 1."
            ),
            expected_output="A structured fact-check report.",
            agent=fact_checker,
            context=[research_task, draft_task],
            output_pydantic=FactCheckReport,
        )

        supervisor_task = Task(
            description=(
                "Review the research packet, draft, and fact-check. Decide whether the report is "
                "safe to send to a human reviewer. Do not approve when important claims are unsupported."
            ),
            expected_output="A structured supervisor decision with issues and revision instructions.",
            agent=supervisor,
            context=[research_task, draft_task, fact_task],
            output_pydantic=SupervisorDecision,
        )

        return Crew(
            agents=[researcher, writer, fact_checker],
            tasks=[research_task, draft_task, fact_task, supervisor_task],
            manager_agent=supervisor,
            process=Process.hierarchical,
            planning=True,
            verbose=False,
        )

    def run(self, topic: str) -> ResearchOutcome:
        result = self.build_crew(topic).kickoff()
        outputs = result.tasks_output

        fact = outputs[-2].pydantic
        supervisor = outputs[-1].pydantic
        if not isinstance(fact, FactCheckReport):
            raise TypeError("Fact checker did not return the required structured output.")
        if not isinstance(supervisor, SupervisorDecision):
            raise TypeError("Supervisor did not return the required structured output.")

        consensus = (
            fact.verification_score >= self.fact_check_threshold
            and supervisor.approved
            and not fact.unsupported_claims
        )
        draft = outputs[1].raw
        return ResearchOutcome(
            report=draft,
            fact_check=fact,
            supervisor=supervisor,
            consensus_approved=consensus,
            task_outputs=[task.raw for task in outputs],
        )
