import { describe, expect, it } from "vitest";
import { isPlatformSuper } from "./platformRole";

describe("platform super", () => {
  it("opens only for the two operator emails", () => {
    expect(isPlatformSuper({ email: "dk@citealpha.com", platform_admin_role: "super" })).toBe(true);
    expect(
      isPlatformSuper({ email: "Admin.Team@citealpha.com", platform_admin_role: "super" }),
    ).toBe(true);
    expect(isPlatformSuper({ email: "owner.team@citealpha.com", platform_admin_role: "super" })).toBe(
      false,
    );
    expect(isPlatformSuper({ email: "dk@citealpha.com", platform_admin_role: "ops" })).toBe(false);
    expect(isPlatformSuper({ email: "owner@desk.test", platform_admin_role: null })).toBe(false);
    expect(isPlatformSuper(null)).toBe(false);
  });
});
