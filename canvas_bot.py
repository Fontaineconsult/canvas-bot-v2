import click


from core.course_root import CanvasCourseRoot


class CanvasBot(CanvasCourseRoot):
    """
    Wraps Canvas Course Root Class
    """
    def __init__(self, course_id: str):
        super().__init__(course_id)

    def start(self):
        self.initialize_course()

    def print_content_tree(self):
        return self.canvas_tree.show_nodes()




if __name__=='__main__':

    @click.command()
    @click.option('--course_id', type=click.INT, help='The course ID to scrape')
    @click.option('--download', type=click.STRING, help='The Location to Download Files to. Default is current directory')
    @click.pass_context
    def main(ctx, course_id, download):
        click.echo(course_id)
        bot = CanvasBot(course_id)
        bot.start()
        bot.print_content_tree()
        click.echo(download)
        if ctx.params.get('download'):
            bot.download_files(download, course_id)





    main()
