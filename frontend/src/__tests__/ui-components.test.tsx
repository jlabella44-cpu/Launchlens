import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/glass-card";

describe("Badge", () => {
  it("renders the themed label for a known state", () => {
    render(<Badge state="approved" />);
    expect(screen.getByText("Cleared for Takeoff")).toBeInTheDocument();
  });

  it("renders the themed label for an underscored state", () => {
    render(<Badge state="awaiting_review" />);
    expect(screen.getByText("Awaiting Clearance")).toBeInTheDocument();
  });

  it("falls back to the de-underscored state name when unlabelled", () => {
    render(<Badge state="pending_ops" />);
    expect(screen.getByText("pending ops")).toBeInTheDocument();
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
