import type { APIRoute } from "astro";
import { skills } from "../../../data/skills";
import { registry } from "../../../data/registry";

const skillRawModules = import.meta.glob<string>("/skills/*/SKILL.md", {
  eager: true,
  query: "?raw",
  import: "default",
});

const skillRawEntries = Object.entries(skillRawModules).map(([path, raw]) => {
  const entrySlug = path.split("/").at(-2) ?? "";

  return { slug: entrySlug, raw };
});

export function getStaticPaths() {
  return skills.map((skill) => ({
    params: { slug: skill.slug },
  }));
}

export const GET: APIRoute = async ({ params }) => {
  const slug = params.slug ?? "";

  // Check local skills first
  const localSkill = skillRawEntries.find((entry) => entry.slug === slug);
  if (localSkill) {
    return new Response(localSkill.raw, {
      headers: {
        "Content-Type": "text/plain; charset=utf-8",
      },
    });
  }

  // Check registry skills
  const registrySkill = registry.find((s) => s.slug === slug);
  if (registrySkill) {
    try {
      const response = await fetch(registrySkill.rawUrl);
      if (!response.ok) {
        throw new Error(
          `Failed to fetch registry skill: ${response.statusText}`,
        );
      }
      const content = await response.text();
      return new Response(content, {
        headers: {
          "Content-Type": "text/plain; charset=utf-8",
        },
      });
    } catch (error) {
      console.error(error);
      return new Response("Error fetching registry skill", { status: 500 });
    }
  }

  return new Response("Skill not found", { status: 404 });
};
