import { Paper, Group, NumberFormatter } from '@mantine/core';
import { TextMdRegular } from '../typography/TextVariants';
import { getFilteredChartTooltipPayload } from '@mantine/charts';
import { dateFormatter } from '@/utils/date-formatter'


interface ChartTooltipProps {
  label: string;
  payload: Record<string, any>[] | undefined;
}

interface payloadComponentProps {
    itemLabel: any;
    itemValue: any;
    itemColor?: string;
}


const PayloadComponent = ({itemLabel, itemValue, itemColor}: payloadComponentProps) => {
    return (
        <Group>
            <TextMdRegular c={itemColor}>{itemLabel}</TextMdRegular>
            <TextMdRegular>
              <NumberFormatter value={itemValue} decimalScale={2} />
            </TextMdRegular>
        </Group>
    )
}

export default function CustomToolTip({ label, payload }: ChartTooltipProps) {
  if (!payload) return null;

  const formattedLabel = dateFormatter(String(label));
  // match_count rides along on the raw datum (not a plotted series), so pull it
  // off any payload entry and show it as context below the metrics.
  const matchCount = payload[0]?.payload?.match_count;

  return (
    <Paper px="md" py="sm" withBorder shadow="md" radius="md">
        <TextMdRegular>
            {formattedLabel}
        </TextMdRegular>
      {getFilteredChartTooltipPayload(payload).map((item: any) => (
        <PayloadComponent key={item.name} itemColor={item.color} itemLabel={item.name} itemValue={item.value} />
      ))}
      {matchCount != null && (
        <Group>
          <TextMdRegular c="dimmed">Matches</TextMdRegular>
          <TextMdRegular><NumberFormatter value={matchCount} thousandSeparator /></TextMdRegular>
        </Group>
      )}
    </Paper>
  );
}
