import React from "react";
import { render, screen } from "@testing-library/react";
import ExternalResultGroup from "../external-result-group";

describe("ExternalResultGroup", () => {
  it("renders title, source and snippet with highlighted query", () => {
    const group = {
      key: "1",
      url: "https://example.com",
      title: "Example Domain",
      source_code: "EXAMPLE",
      snippet: "This is an Example Domain sample",
      score: 100,
    };
    render(<ExternalResultGroup group={group} query="Example" />);
    expect(screen.getByText(/Example Domain/)).toBeInTheDocument();
    expect(screen.getByText(/EXAMPLE/)).toBeInTheDocument();
    expect(screen.getByText(/sample/)).toBeInTheDocument();
  });
});
