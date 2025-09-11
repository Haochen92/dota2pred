import { parseISO, format, isValid } from 'date-fns';

const dateFormatter = (dateString: string) => {
    const formattedDate = parseISO(dateString);
    return isValid(formattedDate) ? format(formattedDate, 'MMM dd yyyy') : dateString;
}

export { dateFormatter };
