import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/glass-card";

describe("Badge", () => {
  it("renders state label", () => {
    render(<Badge state="approved" />);
    expect(screen.getByText("approved")).toBeInTheDocument();
  });

  it("formats underscored states", () => {
    render(<Badge state="awaiting_review" />);
    expect(screen.getByText("awaiting review")).toBeInTheDocument();
  });
});

describe("Button", () => {
  it("renders children", () => {
    render(<Button>Click me</Button>);
    expect(screen.getByText("Click me")).toBeInTheDocument();
  });

  it("shows spinner when loading", () => {
    render(<Button loading>Submit</Button>);
    const button = screen.getByText("Submit").closest("button");
    expect(button).toBeDisabled();
    expect(button?.querySelector("svg")).toBeTruthy();
  });

  it("is disabled when disabled prop set", () => {
    render(<Button disabled>Nope</Button>);
    expect(screen.getByText("Nope").closest("button")).toBeDisabled();
  });
});

describe("GlassCard", () => {
  it("renders children", () => {
    render(<GlassCard>Card content</GlassCard>);
    expect(screen.getByText("Card content")).toBeInTheDocument();
  });

  it("applies custom className", () => {
    render(<GlassCard className="test-class">Content</GlassCard>);
    expect(screen.getByText("Content").closest("div")).toHaveClass("test-class");
  });
});
