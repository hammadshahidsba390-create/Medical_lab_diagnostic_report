import Link from "next/link";

export default function Home() {
  return (
    <main>
      <h1>Understand your lab report</h1>
      <p className="lead">
        Upload a report, check the values, and prepare questions for your doctor. Values are compared with the
        range printed on your own report.
      </p>
      <div className="notice">
        <strong>Educational information only.</strong> This is not a diagnosis. Please discuss your results with
        your doctor.
      </div>
      <p>
        <Link href="/register">Create an account</Link> or <Link href="/login">log in</Link>.
      </p>
    </main>
  );
}
