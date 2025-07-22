import Image from "next/image";

export default function HeroIcon ({hero_id}) {
    return <Image
                src={`/icons/heros/${hero_id}.svg`}
                height={400}
                width={400}
                alt={`${hero_id}.svg`}
            />
}
