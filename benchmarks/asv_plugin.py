"""ASV plugin that adds the project-owned feregion benchmark summary page."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from asv.publishing import OutputPublisher

from .reporting import build_publisher_payload, install_report_extension


class FeregionSummary(OutputPublisher):
    """Publish a compact project summary beside ASV's native technical views."""

    name = "feregion"
    button_label = "feregion summary"
    description = "Project benchmark overview and curated scaling links"
    order = 4

    @classmethod
    def publish(
        cls,
        conf: Any,
        repo: Any,
        benchmarks: Any,
        graphs: Any,
        revisions: Any,
    ) -> None:
        """Write summary data and install the additive static-page assets."""

        html_dir = Path(conf.html_dir)
        payload = build_publisher_payload(
            html_dir=html_dir,
            benchmarks=benchmarks,
            graphs=graphs,
            revisions=revisions,
            repo=repo,
        )
        (html_dir / "feregion.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        install_report_extension(html_dir)
