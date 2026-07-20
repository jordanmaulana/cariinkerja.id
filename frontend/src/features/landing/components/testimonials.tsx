import { Quote } from "lucide-react";

import nurliantoAldiAvatar from "@/assets/testimonial-nurlianto-aldi.jpg";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { useInView } from "@/features/landing/hooks";
import { cn } from "@/lib/utils";

type Testimonial = {
  name: string;
  avatar: string;
  quote: string;
};

const TESTIMONIALS: Testimonial[] = [
  {
    name: "Nurlianto Aldi",
    avatar: nurliantoAldiAvatar,
    quote:
      "Secara overall, cariinkerja.id cukup ngebantu, Mas. Terutama dalam hal mempersingkat waktu dalam pencarian kerja yang cocok. Apalagi udah ada feedback kecocokan antara loker dan CV yang kita punya. Fitur filter nya juga ngebantu, saya biasa pake filter yang dimana skor CV saya berada di atas 75.",
  },
];

export function Testimonials() {
  const { ref, show } = useInView<HTMLDivElement>();
  const single = TESTIMONIALS.length === 1;

  return (
    <section id="testimonials" className="border-y border-border/60 bg-muted/20">
      <div
        ref={ref}
        className={cn(
          "mx-auto max-w-6xl px-6 py-16 lg:py-20",
          "motion-safe:transition-all motion-safe:duration-700 motion-safe:ease-out",
          !show && "motion-safe:translate-y-6 motion-safe:opacity-0",
        )}
      >
        <div className="mx-auto max-w-2xl text-center">
          <Badge variant="outline" className="mb-4">
            <Quote className="size-3" />
            Kata mereka
          </Badge>
          <h2 className="font-heading text-3xl font-semibold tracking-tight sm:text-4xl">
            Yang udah nyoba, ngomong apa?
          </h2>
          <p className="mt-3 text-muted-foreground">
            Kata pengguna yang beneran nyari kerja
            pake cariinkerja.id.
          </p>
        </div>
        <div
          className={cn(
            "mt-10 grid gap-6 md:grid-cols-2 lg:grid-cols-3",
            single && "mx-auto max-w-2xl md:grid-cols-1 lg:grid-cols-1",
          )}
        >
          {TESTIMONIALS.map((t, i) => (
            <TestimonialCard key={t.name} testimonial={t} delay={i * 90} />
          ))}
        </div>
      </div>
    </section>
  );
}

function TestimonialCard({
  testimonial,
  delay,
}: {
  testimonial: Testimonial;
  delay: number;
}) {
  return (
    <Card
      className="shadow-lg transition-shadow hover:shadow-xl motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-bottom-3 motion-safe:duration-500"
      style={{ animationDelay: `${delay}ms`, animationFillMode: "backwards" }}
    >
      <CardContent className="flex h-full flex-col px-6 py-6">
        <figure className="flex h-full flex-col">
          <Quote
            aria-hidden
            className="size-6 shrink-0 text-muted-foreground/40"
          />
          <blockquote className="mt-4 flex-1 text-pretty leading-relaxed">
            {testimonial.quote}
          </blockquote>
          <figcaption className="mt-6 flex items-center gap-3 border-t border-border/60 pt-4">
            <img
              src={testimonial.avatar}
              alt=""
              loading="lazy"
              width={44}
              height={44}
              className="size-11 shrink-0 rounded-full object-cover"
            />
            <cite className="font-medium not-italic">{testimonial.name}</cite>
          </figcaption>
        </figure>
      </CardContent>
    </Card>
  );
}
