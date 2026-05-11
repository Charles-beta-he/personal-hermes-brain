import type { APIRoute } from "astro";
import installScript from "../../install.sh?raw";
import { skills } from "../data/skills";

export const GET: APIRoute = ({ request }) => {
  const allSkills = skills.map((s) => s.slug).join(" ");
  const body =
    installScript
      .replace(/ALL_SKILLS=".*"/, `ALL_SKILLS="${allSkills}"`)
      .trim() + "\n";

  return new Response(body, {
    headers: {
      "Content-Type": "text/x-shellscript; charset=utf-8",
    },
  });
};
