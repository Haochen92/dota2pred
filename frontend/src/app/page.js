import { redirect } from 'next/navigation';

export const metadata = {
  title: 'Dota Oracle - Home',
  description: 'Welcome to the Dota Oracle match prediction tool.',
};

export default function HomePage() {
  redirect('/match-tracker');
}
