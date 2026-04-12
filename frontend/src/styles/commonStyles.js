import { theme } from './theme';

export const commonStyles = {
    fullContainer: {
        backgroundColor: theme.colors.background,
        minHeight: '100vh',
        width: '100vw',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        padding: '60px 20px',
        fontFamily: theme.fonts.main,
        boxSizing: 'border-box',
        color: theme.colors.text
    },
    cardBase: {
        backgroundColor: theme.colors.card,
        borderRadius: '16px',
        border: `1px solid ${theme.colors.border}`,
        overflow: 'hidden'
    },
    flexCenter: {
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center'
    }
};